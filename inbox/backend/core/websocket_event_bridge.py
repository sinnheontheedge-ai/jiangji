"""
WebSocket事件桥接器 - 将WebSocket事件发布到EventBus

职责：
1. 接收WebSocket的订单更新回调
2. 接收WebSocket的持仓更新回调
3. 接收WebSocket的账户更新回调
4. 将事件发布到EventBus，供OrderMonitor等模块订阅
"""
from typing import Dict, Any
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.event_bus import EventBus
from core.database import get_db, Order, Position
from core.auto_replenish import AutoReplenishManager


class WebSocketEventBridge:
    """WebSocket事件桥接器"""
    
    def __init__(self):
        """初始化桥接器"""
        self.event_bus = EventBus.get_instance()
        logger.info("✅ WebSocket事件桥接器初始化完成")
    
    async def on_account_update(self, data: Dict[str, Any]):
        """
        处理账户更新事件
        
        Args:
            data: 账户更新数据
                {
                    "balance": 1000.0,
                    "available_balance": 800.0,
                    ...
                }
        """
        try:
            logger.debug(f"💰 账户余额更新: {data}")
            
            # 发布账户余额更新事件
            await self.event_bus.publish("account.balance_updated", data)
            
        except Exception as e:
            logger.error(f"❌ 处理账户更新失败: {e}")
    
    async def on_order_update(self, data: Dict[str, Any]):
        """
        处理订单更新事件
        
        Args:
            data: 订单更新数据
                {
                    "symbol": "BTCUSDT",
                    "order_id": "12345",
                    "order_status": "FILLED",
                    "execution_type": "TRADE",
                    ...
                }
        """
        try:
            order_id = data.get("order_id")
            order_status = data.get("order_status")
            execution_type = data.get("execution_type")
            
            logger.debug(f"📋 订单更新: order_id={order_id}, status={order_status}, type={execution_type}")
            
            # 发布订单更新事件
            await self.event_bus.publish("order.updated", data)
            
            # 如果订单成交，查询数据库获取position_id
            if order_status == "FILLED":
                async for db in get_db():
                    try:
                        # 查询订单
                        result = await db.execute(
                            select(Order).where(Order.exchange_order_id == str(order_id))
                        )
                        order = result.scalar_one_or_none()
                        
                        if order:
                            # 更新订单状态
                            order.status = "FILLED"
                            # P0修复: 先commit再 publish，确保数据一致性
                            await db.commit()
                            
                            # 发布订单成交事件
                            await self.event_bus.publish(
                                f"order:filled:{order.id}",
                                {
                                    "order_id": order.id,
                                    "position_id": order.position_id,
                                    "symbol": data.get("symbol"),
                                    "side": data.get("side"),
                                    "status": "FILLED",
                                    "exchange_order_id": order_id
                                }
                            )
                            
                            logger.info(f"✅ 发布订单成交事件: order_id={order.id}, position_id={order.position_id}")
                        else:
                            logger.warning(f"⚠️ 订单 {order_id} 不存在于数据库")
                    
                    finally:
                        break  # 只执行一次
        
        except Exception as e:
            logger.error(f"❌ 处理订单更新失败: {e}")
    
    async def on_position_update(self, data: Dict[str, Any]):
        """
        处理持仓更新事件
        
        Args:
            data: 持仓更新数据
                {
                    "symbol": "BTCUSDT",
                    "position_amount": 0,
                    "entry_price": 50000.0,
                    "unrealized_pnl": 0,
                    ...
                }
        """
        try:
            symbol = data.get("symbol")
            position_amount = data.get("position_amount", 0)
            
            logger.debug(f"📊 持仓更新: symbol={symbol}, amount={position_amount}")
            
            # 发布持仓更新事件
            await self.event_bus.publish("position.updated", data)
            
            # 如果持仓数量不为0，检查Step Lock
            if position_amount != 0:
                mark_price = data.get("mark_price")  # 使用标记价格
                if mark_price:
                    async for db in get_db():
                        try:
                            # 查询持仓
                            result = await db.execute(
                                select(Position).where(
                                    Position.symbol == symbol,
                                    Position.is_open == True
                                )
                            )
                            position = result.scalar_one_or_none()
                            
                            if position:
                                # 检查Step Lock
                                from core.step_lock_manager import get_step_lock_coordinator
                                
                                step_lock_coordinator = get_step_lock_coordinator(db)
                                trigger_result = await step_lock_coordinator.check_and_trigger_step_lock(
                                    position_id=position.id,
                                    current_price=float(mark_price)
                                )
                                
                                if trigger_result and trigger_result.get("triggered"):
                                    # Step Lock触发，更新止损订单
                                    logger.info(
                                        f"🔒 Step Lock触发: position_id={position.id} "
                                        f"level={trigger_result['new_level']} "
                                        f"new_sl={trigger_result['new_sl_price']}"
                                    )
                                    
                                    # 更新止损订单
                                    from plugins.risk_engine.tpsl_manager import TPSLManager
                                    tpsl_manager = TPSLManager(db, None)  # client会在需要时传入
                                    await tpsl_manager.update_stop_loss(
                                        position_id=position.id,
                                        new_stop_loss_price=trigger_result['new_sl_price']
                                    )
                                    
                                    # 发布Step Lock触发事件
                                    await self.event_bus.publish(
                                        "step_lock.triggered",
                                        trigger_result
                                    )
                        
                        finally:
                            break  # 只执行一次
            
            # 如果持仓数量为0，说明持仓已平仓
            if position_amount == 0:
                async for db in get_db():
                    try:
                        # 查询持仓
                        result = await db.execute(
                            select(Position).where(
                                Position.symbol == symbol,
                                Position.is_open == True
                            )
                        )
                        position = result.scalar_one_or_none()
                        
                        if position:
                            # 更新持仓状态
                            position.is_open = False
                            await db.commit()
                            
                            # 发布持仓平仓事件
                            await self.event_bus.publish(
                                f"position:closed:{position.id}",
                                {
                                    "position_id": position.id,
                                    "symbol": symbol,
                                    "side": position.side,
                                    "quantity": 0
                                }
                            )
                            
                            logger.info(f"✅ 发布持仓平仓事件: position_id={position.id}, symbol={symbol}")
                            
                            # 触发自动补足余额检查
                            auto_replenish = AutoReplenishManager(db)
                            await auto_replenish.on_position_closed(position.account_id)
                    
                    finally:
                        break  # 只执行一次
        
        except Exception as e:
            logger.error(f"❌ 处理持仓更新失败: {e}")


# 全局桥接器实例
websocket_event_bridge = WebSocketEventBridge()
