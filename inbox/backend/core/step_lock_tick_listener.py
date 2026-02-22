"""
Step Lock Tick监听器 - 订阅tick事件并触发Step Lock检查
"""
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.event_bus import EventBus
from core.database import Position, get_db
from core.step_lock_manager import get_step_lock_coordinator


class StepLockTickListener:
    """Step Lock Tick监听器"""
    
    def __init__(self):
        """初始化监听器"""
        self.event_bus = EventBus.get_instance()
        logger.info("✅ Step Lock Tick监听器初始化完成")
    
    async def start(self):
        """启动监听器，订阅tick事件"""
        await self.event_bus.subscribe("risk:step_lock:tick:*", self._on_tick)
        logger.info("✅ Step Lock Tick监听器已启动，监听 risk:step_lock:tick:* 事件")
    
    async def _on_tick(self, channel: str, data: dict):
        """
        处理tick事件，检查所有相关持仓的Step Lock状态
        
        Args:
            channel: 事件频道，如 "risk:step_lock:tick:BTCUSDT"
            data: tick数据 {"symbol": "BTCUSDT", "price": 50000.0, "timestamp": ...}
        """
        try:
            symbol = data.get('symbol')
            current_price = data.get('price')
            
            if not symbol or not current_price:
                return
            
            # 查询所有该交易对的开仓持仓
            async for db in get_db():
                try:
                    stmt = select(Position).where(
                        Position.symbol == symbol,
                        Position.is_open == True
                    )
                    result = await db.execute(stmt)
                    positions = result.scalars().all()
                    
                    if not positions:
                        return
                    
                    # 检查每个持仓的Step Lock状态
                    coordinator = get_step_lock_coordinator(db)
                    
                    for position in positions:
                        trigger_result = await coordinator.check_and_trigger_step_lock(
                            position_id=position.id,
                            current_price=current_price
                        )
                        
                        if trigger_result and trigger_result.get('triggered'):
                            # 触发了新档位，发布事件
                            await self.event_bus.publish(
                                "risk:step_lock:triggered",
                                {
                                    "position_id": position.id,
                                    "instance_id": position.instance_id,
                                    "symbol": symbol,
                                    "old_level": trigger_result['old_level'],
                                    "new_level": trigger_result['new_level'],
                                    "new_sl_price": trigger_result['new_sl_price'],
                                    "current_price": trigger_result['current_price']
                                }
                            )
                            
                            logger.info(
                                f"🔔 Step Lock触发事件已发布: position_id={position.id} "
                                f"档位{trigger_result['old_level']}→{trigger_result['new_level']}"
                            )
                    
                    break  # 只需要一次数据库会话
                    
                except Exception as e:
                    logger.error(f"❌ Step Lock tick处理失败: {e}")
                    await db.rollback()
                    
        except Exception as e:
            logger.error(f"❌ Step Lock tick监听器异常: {e}")


# 全局实例
step_lock_tick_listener = StepLockTickListener()
