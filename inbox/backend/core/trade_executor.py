"""
交易执行协调器 - 集成所有引擎的核心执行层
"""
import asyncio
from typing import Dict, Optional, Any
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.event_bus import EventBus
from core.database import get_db, Account, Instance, FundConfig, Order, Position
from plugins.fund_engine.compounding import CompoundingEngine, CompoundingMode
from plugins.fund_engine.profit_extract import ProfitExtractionEngine, ExtractionMode
from plugins.risk_engine.tpsl_manager import TPSLManager
from plugins.execution_engine.leverage_manager import LeverageManager


class TradeExecutor:
    """
    交易执行协调器
    
    职责：
    1. 监听策略生成的交易信号
    2. 调用复利引擎计算保证金
    3. 调用杠杆管理器设置杠杆
    4. 调用风控引擎计算止盈止损
    5. 执行市价单开仓
    6. 保存订单和持仓到数据库
    """
    
    def __init__(self):
        """初始化交易执行协调器"""
        self.event_bus = EventBus.get_instance()
        
        # 为每个实例存储引擎实例
        self.compounding_engines: Dict[int, CompoundingEngine] = {}
        self.tpsl_managers: Dict[int, TPSLManager] = {}
        self.leverage_managers: Dict[int, LeverageManager] = {}
        
        # 为每个账户存储币安客户端
        self.binance_clients: Dict[int, Any] = {}
        
        logger.info("✅ 交易执行协调器初始化完成")
    
    async def start(self):
        """启动执行协调器，订阅交易信号"""
        await self.event_bus.subscribe("signal:trade:*", self._on_trade_signal)
        logger.info("✅ 交易执行协调器已启动，监听 signal:trade:* 事件")
    
    async def load_engines_for_instance(self, instance_id: int, db: AsyncSession):
        """
        为指定实例加载所有引擎
        
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
            
            # 初始化币安客户端
            if account_id not in self.binance_clients:
                from core.binance_client import BinanceClient
                from core.binance_websocket import BinanceWebSocket
                from core.websocket_event_bridge import websocket_event_bridge
                
                self.binance_clients[account_id] = BinanceClient(
                    api_key=account.api_key,
                    api_secret=account.api_secret,
                    testnet=account.testnet,
                    proxy=account.proxy if hasattr(account, 'proxy') else None
                )
                logger.info(f"✅ 为账户 {account_id} 初始化币安客户端")
                
                # 注册客户端到OrderMonitor
                from core.order_monitor import order_monitor
                order_monitor.register_client(account_id, self.binance_clients[account_id])
                logger.info(f"✅ 为账户 {account_id} 注册OrderMonitor客户端")
                
                # 初始化WebSocket客户端并设置回调
                ws_client = BinanceWebSocket(
                    api_key=account.api_key,
                    api_secret=account.api_secret,
                    testnet=account.testnet,
                    proxy=account.proxy if hasattr(account, 'proxy') else None
                )
                await ws_client.connect()
                
                # 设置订单和持仓更新回调
                ws_client.set_order_update_callback(websocket_event_bridge.on_order_update)
                ws_client.set_position_update_callback(websocket_event_bridge.on_position_update)
                
                # 订阅用户数据流
                await ws_client.subscribe_user_data_stream()
                logger.info(f"✅ 为账户 {account_id} 初始化WebSocket并订阅用户数据流")
            
            # 查询资金管理配置
            result = await db.execute(select(FundConfig).where(FundConfig.account_id == account_id))
            fund_config = result.scalar_one_or_none()
            
            # 初始化复利引擎
            if fund_config:
                self.compounding_engines[instance_id] = CompoundingEngine({
                    "mode": fund_config.compounding_mode,
                    "compound_ratio": fund_config.compound_ratio,
                    "initial_base": fund_config.initial_base,
                    "position_percent": fund_config.position_percent,
                    "concurrent_positions": fund_config.concurrent_positions
                })
                logger.info(f"✅ 为实例 {instance_id} 初始化复利引擎")
            else:
                # 使用默认配置
                self.compounding_engines[instance_id] = CompoundingEngine({
                    "mode": "perpetual",
                    "compound_ratio": 20,
                    "initial_base": 1000,
                    "position_percent": 10,
                    "concurrent_positions": 1
                })
                logger.warning(f"⚠️ 实例 {instance_id} 未配置资金管理，使用默认配置")
            
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
            
            # 初始化杠杆管理器
            leverage = instance.leverage if hasattr(instance, 'leverage') and instance.leverage else 10
            self.leverage_managers[instance_id] = LeverageManager({
                "default_leverage": leverage,
                "max_leverage": 125,
                "enable_auto_delever": True
            })
            logger.info(f"✅ 为实例 {instance_id} 初始化杠杆管理器 (杠杆={leverage}x)")
            
        except Exception as e:
            logger.error(f"❌ 为实例 {instance_id} 加载引擎失败: {e}")
            raise
    
    async def _on_trade_signal(self, channel: str, data: dict):
        """
        处理交易信号
        
        Args:
            channel: 事件频道，如 "signal:trade:123"
            data: 信号数据
                {
                    "instance_id": 123,
                    "action": "BUY" | "SELL",
                    "symbol": "BTCUSDT",
                    "quantity": 0.001,  # 可选
                    "price": 50000.0,   # 可选
                    "reason": "金叉信号"
                }
        """
        try:
            # 解析实例ID
            parts = channel.split(":")
            if len(parts) < 3:
                logger.error(f"❌ 无效的信号频道: {channel}")
                return
            
            instance_id = int(parts[2])
            
            logger.info(f"📊 收到交易信号: 实例={instance_id}, 动作={data['action']}, 交易对={data['symbol']}")
            
            # 检查引擎是否已加载
            if instance_id not in self.compounding_engines:
                logger.error(f"❌ 实例 {instance_id} 的引擎未加载")
                return
            
            # 获取数据库会话
            async for db in get_db():
                try:
                    # 执行交易
                    await self._execute_trade(instance_id, data, db)
                finally:
                    await db.close()
                break
            
        except Exception as e:
            logger.error(f"❌ 处理交易信号失败: {e}")
    
    async def _execute_trade(self, instance_id: int, signal: dict, db: AsyncSession):
        """
        执行交易
        
        Args:
            instance_id: 实例ID
            signal: 交易信号
            db: 数据库会话
        """
        try:
            # 1. 查询实例和账户
            result = await db.execute(select(Instance).where(Instance.id == instance_id))
            instance = result.scalar_one_or_none()
            if not instance:
                logger.error(f"❌ 实例 {instance_id} 不存在")
                return
            
            account_id = instance.account_id
            result = await db.execute(select(Account).where(Account.id == account_id))
            account = result.scalar_one_or_none()
            if not account:
                logger.error(f"❌ 账户 {account_id} 不存在")
                return
            
            # 2. 获取币安客户端
            client = self.binance_clients.get(account_id)
            if not client:
                logger.error(f"❌ 账户 {account_id} 的币安客户端未初始化")
                return
            
            # 3. P0修复: 单仓模式检查 - 必须在下单前检查是否已有持仓
            if instance.position_mode == "single":
                result = await db.execute(
                    select(Position).where(
                        Position.instance_id == instance_id,
                        Position.is_open == True
                    )
                )
                existing_position = result.scalar_one_or_none()
                if existing_position:
                    logger.warning(
                        f"⚠️ 单仓模式拒绝开仓: 实例{instance_id}已有持仓 "
                        f"(symbol={existing_position.symbol}, side={existing_position.side})"
                    )
                    await self.event_bus.publish(
                        "trade:rejected",
                        {
                            "instance_id": instance_id,
                            "reason": "single_position_mode_violation",
                            "existing_position": {
                                "symbol": existing_position.symbol,
                                "side": existing_position.side,
                                "size": existing_position.size
                            },
                            "signal": signal
                        }
                    )
                    return
            
            # 4. 获取账户余额
            balance_info = await client.get_account_balance()
            available_balance = balance_info.get('available_balance', 0)
            
            logger.info(f"💰 账户余额: {available_balance} USDT")
            
            # 5. 调用复利引擎计算保证金
            compounding_engine = self.compounding_engines[instance_id]
            is_single_position = (instance.position_mode == "single")
            margin = compounding_engine.calculate_margin(
                available_balance=float(available_balance),
                is_single_position=is_single_position
            )
            
            logger.info(f"📈 复利引擎计算保证金: {margin} USDT")
            
            # 6. P0修复: 资金安全门禁 - 下单前必须检查余额
            # 查询资金配置
            result = await db.execute(
                select(FundConfig).where(FundConfig.account_id == account_id)
            )
            fund_config = result.scalar_one_or_none()
            
            # 计算所需保证金
            leverage_manager = self.leverage_managers[instance_id]
            leverage = leverage_manager.get_leverage(signal['symbol'])
            
            current_price = signal.get('price')
            if not current_price:
                ticker_info = await client.get_ticker_price(signal['symbol'])
                current_price = float(ticker_info['price'])
            
            # P0修复: 使用Decimal进行精度计算
            from decimal import Decimal
            margin_decimal = Decimal(str(margin))
            leverage_decimal = Decimal(str(leverage))
            price_decimal = Decimal(str(current_price))
            
            quantity_decimal = (margin_decimal * leverage_decimal) / price_decimal
            # TODO: 按交易所exchange filters截断，这里临时使用round
            quantity = float(quantity_decimal.quantize(Decimal('0.001')))
            
            required_margin_decimal = (quantity_decimal * price_decimal) / leverage_decimal
            required_margin = float(required_margin_decimal)
            
            # 门禁检查
            min_reserve = fund_config.min_reserve_balance if fund_config else 10.0
            
            if available_balance < required_margin:
                logger.error(
                    f"❌ 资金门禁拒绝: 余额不足 "
                    f"(available={available_balance}, required={required_margin})"
                )
                await self.event_bus.publish(
                    "trade:rejected",
                    {
                        "instance_id": instance_id,
                        "reason": "insufficient_balance",
                        "available_balance": available_balance,
                        "required_margin": required_margin
                    }
                )
                return
            
            if available_balance - required_margin < min_reserve:
                logger.error(
                    f"❌ 资金门禁拒绝: 保留余额不足 "
                    f"(remaining={available_balance - required_margin}, min_reserve={min_reserve})"
                )
                await self.event_bus.publish(
                    "trade:rejected",
                    {
                        "instance_id": instance_id,
                        "reason": "insufficient_reserve",
                        "remaining_balance": available_balance - required_margin,
                        "min_reserve": min_reserve
                    }
                )
                return
            
            logger.info(f"✅ 资金门禁通过: available={available_balance}, required={required_margin}, reserve={min_reserve}")
            
            # 7. 设置杠杆
            await client.set_leverage(signal['symbol'], leverage)
            logger.info(f"⚙️ 设置杠杆: {leverage}x")
            
            logger.info(f"📊下单数量: {quantity} (价格={current_price}, 保证金={margin}, 杠杆={leverage}x)")          
            # 7. 调用风控引擎计算止盈止损
            tpsl_manager = self.tpsl_managers[instance_id]
            side = "LONG" if signal['action'] == "BUY" else "SHORT"
            tpsl_prices = tpsl_manager.calculate_tpsl(
                entry_price=current_price,
                side=side
            )
            
            tp_price = tpsl_prices['take_profit']
            sl_price = tpsl_prices['stop_loss']
            
            logger.info(f"🎯 止盈止损: TP={tp_price}, SL={sl_price}")
            
            # 8. P0修复: 执行市价单开仓 - 必须使用clientOrderId保证幂等性
            order_side = "buy" if signal['action'] == "BUY" else "sell"
            
            # 生成幂等性键
            import uuid
            import time
            client_order_id = f"open_{instance_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            logger.info(
                f"📝 准备开仓: symbol={signal['symbol']}, side={order_side}, "
                f"quantity={quantity}, clientOrderId={client_order_id}"
            )
            
            order_result = await client.create_market_order(
                symbol=signal['symbol'],
                side=order_side,
                amount=quantity,
                reduce_only=False,  # 开仓订单
                client_order_id=client_order_id
            )
            
            logger.info(f"✅ 市价单已提交: {order_result}")
            
            # 9. 保存订单到数据库
            order = Order(
                instance_id=instance_id,
                account_id=account_id,
                symbol=signal['symbol'],
                client_order_id=client_order_id,  # P0修复: 保存clientOrderId
                exchange_order_id=str(order_result['orderId']),  # P0修复: 保存交易所订单ID
                side=order_side,
                order_type="MARKET",
                quantity=quantity,
                price=current_price,
                status="FILLED"
            )
            db.add(order)
            await db.flush()
            
            # 10. 创建持仓记录
            position = Position(
                instance_id=instance_id,
                account_id=account_id,
                symbol=signal['symbol'],
                side=side,
                quantity=quantity,
                entry_price=current_price,
                leverage=leverage,
                take_profit=tp_price,
                stop_loss=sl_price,
                is_open=True
            )
            db.add(position)
            await db.flush()
            
            position_id = position.id
            
            logger.info(f"✅ 持仓记录已创建: ID={position_id}")
            
            # 11. 下止盈止损订单
            # 止盈订单
            tp_client_order_id = f"tp_{instance_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            tp_order_result = await client.create_limit_order(
                symbol=signal['symbol'],
                side="SELL" if order_side == "BUY" else "BUY",
                quantity=quantity,
                price=tp_price,
                reduce_only=True,
                client_order_id=tp_client_order_id
            )
            
            logger.info(f"✅ 止盈订单已提交: {tp_order_result}")
            
            # 止损订单
            sl_client_order_id = f"sl_{instance_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            sl_order_result = await client.create_stop_market_order(
                symbol=signal['symbol'],
                side="SELL" if order_side == "BUY" else "BUY",
                quantity=quantity,
                stop_price=sl_price,
                reduce_only=True,
                client_order_id=sl_client_order_id
            )
            
            logger.info(f"✅ 止损订单已提交: {sl_order_result}")
            
            # 12. 保存止盈止损订单
            tp_order = Order(
                instance_id=instance_id,
                account_id=account_id,
                symbol=signal['symbol'],
                client_order_id=tp_client_order_id,  # P0修复: 保存clientOrderId
                exchange_order_id=str(tp_order_result['orderId']),  # 记录交易所订单ID
                side="SELL" if order_side == "BUY" else "BUY",
                order_type="TAKE_PROFIT",
                quantity=quantity,
                price=tp_price,
                status="NEW",
                position_id=position_id,
                reduce_only=True  # P0修复: 明确标记reduceOnly
            )
            db.add(tp_order)
            
            sl_order = Order(
                instance_id=instance_id,
                account_id=account_id,
                symbol=signal['symbol'],
                client_order_id=sl_client_order_id,  # P0修复: 保存clientOrderId
                exchange_order_id=str(sl_order_result['orderId']),  # 记录交易所订单ID
                side="SELL" if order_side == "BUY" else "BUY",
                order_type="STOP_MARKET",
                quantity=quantity,
                price=sl_price,
                status="NEW",
                position_id=position_id,
                reduce_only=True  # P0修复: 明确标记reduceOnly
            )
            db.add(sl_order)
            
            await db.commit()
            
            logger.info(f"🎉 交易执行完成: {signal['symbol']} {order_side} {quantity}")
            
            # 13. 注册持仓到OrderMonitor
            from core.order_monitor import order_monitor
            order_monitor.register_position(
                position_id=position_id,
                account_id=account_id,
                tp_order_id=tp_order.id,
                sl_order_id=sl_order.id
            )
            logger.info(f"✅ 持仓 {position_id} 已注册到OrderMonitor")
            
            # 14. 初始化Step Lock（如果启用）
            if instance.use_step_locking:
                from core.step_lock_manager import get_step_lock_coordinator
                
                step_lock_coordinator = get_step_lock_coordinator(db)
                step_lock_success = await step_lock_coordinator.initialize_step_lock(
                    position_id=position_id,
                    entry_price=current_price,
                    side=side,
                    step_lock_config=instance.step_lock_config
                )
                
                if step_lock_success:
                    logger.info(f"✅ Step Lock已初始化: position_id={position_id}")
                else:
                    logger.error(f"❌ Step Lock初始化失败: position_id={position_id}")
            else:
                logger.debug(f"⏭️ 实例 {instance_id} 未启用Step Lock")
            
            # 14. P0修复: 先commit再发布事件，确保数据一致性
            await db.commit()
            logger.info(f"✅ 数据库事务已提交")
            
            # 15. 发布交易完成事件
            await self.event_bus.publish(
                f"trade:completed:{instance_id}",
                {
                    "instance_id": instance_id,
                    "position_id": position_id,
                    "symbol": signal['symbol'],
                    "side": side,
                    "quantity": quantity,
                    "entry_price": current_price,
                    "take_profit": tp_price,
                    "stop_loss": sl_price
                }
            )
            
            # 16. 发布order.created事件
            await self.event_bus.publish(
                "order.created",
                {
                    "order_id": order.id,
                    "instance_id": instance_id,
                    "symbol": signal['symbol'],
                    "side": order_side,
                    "quantity": quantity,
                    "price": current_price,
                    "status": "FILLED"
                }
            )
            
            # 17. 发布order.filled事件
            await self.event_bus.publish(
                "order.filled",
                {
                    "order_id": order.id,
                    "instance_id": instance_id,
                    "symbol": signal['symbol'],
                    "side": order_side,
                    "filled_quantity": quantity,
                    "average_price": current_price
                }
            )
            
        except Exception as e:
            logger.error(f"❌ 执行交易失败: {e}")
            await db.rollback()
            
            # P0修复: 如果是下单成功但DB写入失败，尝试撤单补偿
            if 'order_result' in locals() and order_result:
                try:
                    logger.warning(f"⚠️ 下单成功但DB写入失败，尝试撤单补偿: order_id={order_result.get('orderId')}")
                    client = self.binance_clients.get(account_id)
                    if client:
                        await client.cancel_order(
                            order_id=str(order_result['orderId']),
                            symbol=signal['symbol']
                        )
                        logger.info(f"✅ 补偿撤单成功: order_id={order_result.get('orderId')}")
                except Exception as cancel_error:
                    logger.error(f"❌ 补偿撤单失败: {cancel_error}")
                    # 发布警告事件
                    await self.event_bus.publish(
                        "trade:compensation_failed",
                        {
                            "instance_id": instance_id,
                            "order_id": order_result.get('orderId'),
                            "symbol": signal['symbol'],
                            "error": str(cancel_error)
                        }
                    )
            raise


# 全局交易执行协调器实例
trade_executor = TradeExecutor()
