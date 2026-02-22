"""
风控监控器 - 使用WebSocket实时监控持仓并触发移动止损和分档锁盈
"""
import asyncio
from typing import Dict, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.event_bus import EventBus
from core.database import get_db, Account, Instance, Position, Order
from core.binance_websocket import BinanceWebSocket
from plugins.risk_engine.tpsl_manager import TPSLManager


class RiskMonitor:
    """
    风控监控器（WebSocket实时版本）
    
    职责：
    1. 订阅币安用户数据流
    2. 实时接收持仓更新
    3. 触发移动止损
    4. 触发分档锁盈
    5. 管理止盈止损订单
    
    特点：
    - 使用WebSocket实时推送，延迟 < 100ms
    - 不再使用轮询，完全事件驱动
    """
    
    def __init__(self):
        """初始化风控监控器"""
        self.event_bus = EventBus.get_instance()
        self.running = False
        
        # 为每个实例存储风控引擎
        self.tpsl_managers: Dict[int, TPSLManager] = {}
        
        # 为每个账户存储WebSocket客户端
        self.ws_clients: Dict[int, BinanceWebSocket] = {}
        
        # 为每个账户存储币安REST客户端
        self.binance_clients: Dict[int, any] = {}
        
        # 追踪每个持仓的峰值价格（用于移动止损）
        self.position_peaks: Dict[int, float] = {}  # position_id -> peak_price
        
        # 持仓ID到实例ID的映射
        self.position_to_instance: Dict[int, int] = {}
        
        # 账户ID到实例ID列表的映射
        self.account_to_instances: Dict[int, list] = {}
        
        logger.info("✅ 风控监控器初始化完成（WebSocket实时版本）")
    
    async def start(self):
        """启动风控监控器"""
        self.running = True
        logger.info("✅ 风控监控器已启动（WebSocket实时推送）")
    
    async def stop(self):
        """停止风控监控器"""
        self.running = False
        
        # 关闭所有WebSocket连接
        for account_id, ws_client in self.ws_clients.items():
            await ws_client.disconnect()
            logger.info(f"🛑 关闭账户 {account_id} 的WebSocket连接")
        
        self.ws_clients.clear()
        logger.info("🛑 风控监控器已停止")
    
    async def load_manager_for_instance(self, instance_id: int, db: AsyncSession):
        """
        为指定实例加载风控引擎并订阅WebSocket
        
        Args:
            instance_id: 实例ID
            db: 数据库会话
        """
        try:
            # 查询实例
            result = await db.execute(select(Instance).where(Instance.id == instance_id))
            instance = result.scalar_one_or_none()
            if not instance:
                logger.error(f"❌ 实例 {instance_id} 不存在")
                return
            
            account_id = instance.account_id
            
            # 查询账户
            result = await db.execute(select(Account).where(Account.id == account_id))
            account = result.scalar_one_or_none()
            if not account:
                logger.error(f"❌ 账户 {account_id} 不存在")
                return
            
            # 初始化币安REST客户端
            if account_id not in self.binance_clients:
                from core.binance_client import BinanceClient
                self.binance_clients[account_id] = BinanceClient(
                    api_key=account.api_key,
                    api_secret=account.api_secret,
                    testnet=account.testnet,
                    proxy=account.proxy_config  # 添加代理配置
                )
                logger.info(f"✅ 为账户 {account_id} 初始化币安REST客户端")
            
            # 初始化风控引擎
            tpsl_config = {
                "take_profit_percent": instance.take_profit if instance.take_profit else 5.0,
                "stop_loss_percent": instance.stop_loss if instance.stop_loss else 2.0,
                "enable_trailing_stop": instance.enable_trailing_stop if hasattr(instance, 'enable_trailing_stop') else False,
                "trailing_stop_percent": instance.trailing_stop_percent if hasattr(instance, 'trailing_stop_percent') else 1.0,
                "use_step_locking": instance.use_step_locking,
                "step_config": instance.step_config if instance.step_config else {}
            }
            self.tpsl_managers[instance_id] = TPSLManager(tpsl_config)
            logger.info(f"✅ 为实例 {instance_id} 初始化风控引擎")
            
            # 初始化WebSocket客户端（每个账户一个）
            if account_id not in self.ws_clients:
                ws_client = BinanceWebSocket(
                    api_key=account.api_key,
                    api_secret=account.api_secret,
                    testnet=account.testnet
                )
                
                # 连接WebSocket
                await ws_client.connect()
                
                # 设置持仓更新回调
                ws_client.set_position_update_callback(
                    lambda data: self._on_position_update(account_id, data)
                )
                
                # 订阅用户数据流
                await ws_client.subscribe_user_data_stream()
                
                self.ws_clients[account_id] = ws_client
                logger.info(f"✅ 为账户 {account_id} 初始化WebSocket客户端并订阅用户数据流")
            
            # 记录账户到实例的映射
            if account_id not in self.account_to_instances:
                self.account_to_instances[account_id] = []
            if instance_id not in self.account_to_instances[account_id]:
                self.account_to_instances[account_id].append(instance_id)
            
            # 加载现有持仓的峰值价格
            await self._load_existing_positions(instance_id, db)
            
            logger.info(f"✅ 为实例 {instance_id} 加载风控监控器完成（WebSocket实时推送）")
            
        except Exception as e:
            logger.error(f"❌ 为实例 {instance_id} 加载风控引擎失败: {e}")
            raise
    
    async def _load_existing_positions(self, instance_id: int, db: AsyncSession):
        """加载现有持仓的峰值价格"""
        try:
            # 查询该实例的所有开仓持仓
            result = await db.execute(
                select(Position).where(
                    Position.instance_id == instance_id,
                    Position.is_open == True
                )
            )
            positions = result.scalars().all()
            
            for position in positions:
                # 初始化峰值价格为入场价格
                self.position_peaks[position.id] = position.entry_price
                self.position_to_instance[position.id] = instance_id
                logger.info(f"📊 加载持仓 {position.id} 峰值价格: {position.entry_price}")
            
        except Exception as e:
            logger.error(f"❌ 加载现有持仓失败: {e}")
    
    async def _on_position_update(self, account_id: int, data: dict):
        """
        处理持仓更新（WebSocket回调）
        
        Args:
            account_id: 账户ID
            data: 持仓更新数据
                {
                    "symbol": "BTCUSDT",
                    "position_amount": 0.001,
                    "entry_price": 50000.0,
                    "unrealized_pnl": 100.0,
                    "position_side": "LONG",
                    "timestamp": 1638747660000
                }
        """
        try:
            symbol = data.get("symbol")
            position_amount = data.get("position_amount")
            entry_price = data.get("entry_price")
            unrealized_pnl = data.get("unrealized_pnl")
            
            logger.info(f"📊 收到持仓更新: {symbol} 数量={position_amount}, 入场价={entry_price}, 未实现盈亏={unrealized_pnl}")
            
            # 获取当前价格（从未实现盈亏反推）
            if position_amount != 0:
                # current_price ≈ entry_price + (unrealized_pnl / position_amount)
                current_price = entry_price + (unrealized_pnl / position_amount)
            else:
                # 持仓已平仓，不处理
                return
            
            # 查找该账户下的所有实例
            instance_ids = self.account_to_instances.get(account_id, [])
            
            # 获取数据库会话
            async for db in get_db():
                try:
                    # 查找该交易对的持仓
                    for instance_id in instance_ids:
                        result = await db.execute(
                            select(Position).where(
                                Position.instance_id == instance_id,
                                Position.symbol == symbol,
                                Position.is_open == True
                            )
                        )
                        position = result.scalar_one_or_none()
                        
                        if position:
                            # 检查风控
                            await self._check_position_risk(
                                position=position,
                                current_price=current_price,
                                instance_id=instance_id,
                                account_id=account_id,
                                db=db
                            )
                
                finally:
                    await db.close()
                break
            
        except Exception as e:
            logger.error(f"❌ 处理持仓更新失败: {e}")
    
    async def _check_position_risk(self, position: Position, current_price: float,
                                   instance_id: int, account_id: int, db: AsyncSession):
        """
        检查持仓风控
        
        Args:
            position: 持仓对象
            current_price: 当前价格
            instance_id: 实例ID
            account_id: 账户ID
            db: 数据库会话
        """
        try:
            position_id = position.id
            
            # 检查引擎是否已加载
            if instance_id not in self.tpsl_managers:
                return
            
            if account_id not in self.binance_clients:
                return
            
            # 获取币安客户端
            client = self.binance_clients[account_id]
            
            # 获取风控引擎
            tpsl_manager = self.tpsl_managers[instance_id]
            
            # 1. 检查移动止损
            if tpsl_manager.config.get('enable_trailing_stop', False):
                await self._check_trailing_stop(
                    position=position,
                    current_price=current_price,
                    tpsl_manager=tpsl_manager,
                    client=client,
                    db=db
                )
            
            # 2. 检查分档锁盈
            if tpsl_manager.config.get('use_step_locking', False):
                await self._check_step_locking(
                    position=position,
                    current_price=current_price,
                    tpsl_manager=tpsl_manager,
                    client=client,
                    db=db
                )
            
        except Exception as e:
            logger.error(f"❌ 检查持仓 {position.id} 风控失败: {e}")
    
    async def _check_trailing_stop(self, position: Position, current_price: float,
                                   tpsl_manager: TPSLManager, client: any, db: AsyncSession):
        """检查移动止损"""
        try:
            position_id = position.id
            
            # 初始化峰值价格
            if position_id not in self.position_peaks:
                self.position_peaks[position_id] = position.entry_price
            
            # 更新峰值价格
            if position.side == "LONG":
                if current_price > self.position_peaks[position_id]:
                    self.position_peaks[position_id] = current_price
            else:  # SHORT
                if current_price < self.position_peaks[position_id]:
                    self.position_peaks[position_id] = current_price
            
            peak_price = self.position_peaks[position_id]
            
            # 计算新的移动止损价格
            new_sl = tpsl_manager.update_trailing_stop(
                current_price=current_price,
                peak_price=peak_price,
                side=position.side,
                current_stop_loss=position.stop_loss
            )
            
            # 如果止损价格有更新
            if new_sl and new_sl != position.stop_loss:
                logger.info(f"📊 移动止损触发: 持仓={position_id}, 旧SL={position.stop_loss}, 新SL={new_sl}")
                
                # 1. 取消旧的止损订单
                result = await db.execute(
                    select(Order).where(
                        Order.position_id == position_id,
                        Order.order_type == "STOP_MARKET",
                        Order.status == "NEW"
                    )
                )
                old_sl_orders = result.scalars().all()
                
                for old_order in old_sl_orders:
                    try:
                        await client.cancel_order(position.symbol, old_order.order_id)
                        old_order.status = "CANCELED"
                        logger.info(f"✅ 取消旧止损订单: {old_order.order_id}")
                    except Exception as e:
                        logger.error(f"❌ 取消旧止损订单失败: {e}")
                
                # 2. 创建新的止损订单
                side = "SELL" if position.side == "LONG" else "BUY"
                new_sl_order = await client.create_stop_market_order(
                    symbol=position.symbol,
                    side=side,
                    quantity=position.quantity,
                    stop_price=new_sl,
                    reduce_only=True
                )
                
                logger.info(f"✅ 创建新止损订单: {new_sl_order}")
                
                # 3. 保存新订单到数据库
                order = Order(
                    instance_id=position.instance_id,
                    account_id=position.account_id,
                    symbol=position.symbol,
                    order_id=str(new_sl_order['orderId']),
                    side=side,
                    order_type="STOP_MARKET",
                    quantity=position.quantity,
                    price=new_sl,
                    status="NEW",
                    position_id=position_id
                )
                db.add(order)
                
                # 4. 更新持仓的止损价格
                position.stop_loss = new_sl
                
                await db.commit()
                
                logger.info(f"✅ 移动止损更新完成: 新SL={new_sl}")
                
                # 发布事件
                await self.event_bus.publish(
                    f"risk:trailing_stop_updated:{position.instance_id}",
                    {
                        "position_id": position_id,
                        "symbol": position.symbol,
                        "old_stop_loss": position.stop_loss,
                        "new_stop_loss": new_sl
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ 移动止损检查失败: {e}")
            await db.rollback()
    
    async def _check_step_locking(self, position: Position, current_price: float,
                                  tpsl_manager: TPSLManager, client: any, db: AsyncSession):
        """检查分档锁盈"""
        try:
            position_id = position.id
            
            # 检查是否触发分档锁盈
            triggered, new_sl, level, message = tpsl_manager.check_step_locking(
                current_price=current_price,
                entry_price=position.entry_price,
                side=position.side,
                current_stop_loss=position.stop_loss
            )
            
            if triggered:
                logger.info(f"🎯 分档锁盈触发: 持仓={position_id}, 档位={level}, 新SL={new_sl}, {message}")
                
                # 1. 取消旧的止损订单
                result = await db.execute(
                    select(Order).where(
                        Order.position_id == position_id,
                        Order.order_type == "STOP_MARKET",
                        Order.status == "NEW"
                    )
                )
                old_sl_orders = result.scalars().all()
                
                for old_order in old_sl_orders:
                    try:
                        await client.cancel_order(position.symbol, old_order.order_id)
                        old_order.status = "CANCELED"
                        logger.info(f"✅ 取消旧止损订单: {old_order.order_id}")
                    except Exception as e:
                        logger.error(f"❌ 取消旧止损订单失败: {e}")
                
                # 2. 创建新的止损订单
                side = "SELL" if position.side == "LONG" else "BUY"
                new_sl_order = await client.create_stop_market_order(
                    symbol=position.symbol,
                    side=side,
                    quantity=position.quantity,
                    stop_price=new_sl,
                    reduce_only=True
                )
                
                logger.info(f"✅ 创建新止损订单: {new_sl_order}")
                
                # 3. 保存新订单到数据库
                order = Order(
                    instance_id=position.instance_id,
                    account_id=position.account_id,
                    symbol=position.symbol,
                    order_id=str(new_sl_order['orderId']),
                    side=side,
                    order_type="STOP_MARKET",
                    quantity=position.quantity,
                    price=new_sl,
                    status="NEW",
                    position_id=position_id
                )
                db.add(order)
                
                # 4. 更新持仓的止损价格
                position.stop_loss = new_sl
                
                await db.commit()
                
                logger.info(f"✅ 分档锁盈更新完成: 档位={level}, 新SL={new_sl}")
                
                # 发布事件
                await self.event_bus.publish(
                    f"risk:step_locking_triggered:{position.instance_id}",
                    {
                        "position_id": position_id,
                        "symbol": position.symbol,
                        "level": level,
                        "new_stop_loss": new_sl,
                        "message": message
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ 分档锁盈检查失败: {e}")
            await db.rollback()


# 全局风控监控器实例
risk_monitor = RiskMonitor()
