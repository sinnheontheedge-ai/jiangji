"""
Step Lock管理器 - 负责Step Lock的初始化、触发检查和状态持久化
"""
from typing import Dict, Optional, List
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from core.database import Position, PositionStepLock
from plugins.risk_engine.tpsl_manager import StepLockManager, StepLockLevel, PositionSide


class StepLockCoordinator:
    """Step Lock协调器 - 连接trade_executor和tpsl_manager"""
    
    def __init__(self, db: AsyncSession):
        """
        初始化Step Lock协调器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        logger.info("✅ Step Lock协调器初始化完成")
    
    async def initialize_step_lock(
        self,
        position_id: int,
        entry_price: float,
        side: str,
        step_lock_config: Dict
    ) -> bool:
        """
        为新开仓位初始化Step Lock
        
        Args:
            position_id: 持仓ID
            entry_price: 开仓价格
            side: 持仓方向 (LONG/SHORT)
            step_lock_config: Step Lock配置
        
        Returns:
            是否成功初始化
        """
        try:
            logger.info(
                f"🔧 初始化Step Lock: position_id={position_id} "
                f"entry_price={entry_price} side={side}"
            )
            
            # 创建Step Lock管理器
            step_lock_manager = StepLockManager(step_lock_config)
            
            # 计算所有档位
            position_side = PositionSide.LONG if side == "LONG" else PositionSide.SHORT
            levels = step_lock_manager.calculate_levels(entry_price, position_side)
            
            # 序列化档位配置
            levels_config = [
                {
                    "level": level.level,
                    "threshold_pct": level.threshold_pct,
                    "lock_pct": level.lock_pct,
                    "threshold_price": level.threshold_price,
                    "lock_price": level.lock_price
                }
                for level in levels
            ]
            
            # 保存到数据库
            step_lock_state = PositionStepLock(
                position_id=position_id,
                current_level=0,  # 初始档位为0
                levels_config=levels_config,
                peak_price=entry_price,  # 初始峰值为开仓价
                last_check_time=datetime.utcnow()
            )
            
            self.db.add(step_lock_state)
            await self.db.commit()
            
            logger.info(
                f"✅ Step Lock初始化成功: position_id={position_id} "
                f"档位数={len(levels)} 初始峰值={entry_price}"
            )
            
            # 打印所有档位信息
            for level in levels:
                logger.debug(
                    f"  档位{level.level}: 触发={level.threshold_price:.2f} "
                    f"锁盈={level.lock_price:.2f}"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Step Lock初始化失败: {e}")
            await self.db.rollback()
            return False
    
    async def check_and_trigger_step_lock(
        self,
        position_id: int,
        current_price: float
    ) -> Optional[Dict]:
        """
        检查并触发Step Lock档位
        
        Args:
            position_id: 持仓ID
            current_price: 当前价格
        
        Returns:
            触发信息（如果触发了新档位），格式: {
                "triggered": True,
                "new_level": 2,
                "new_sl_price": 50500.0,
                "old_level": 1
            }
        """
        try:
            logger.debug(
                f"🔍 检查Step Lock: position_id={position_id} "
                f"current_price={current_price}"
            )
            
            # 查询Step Lock状态
            stmt = select(PositionStepLock).where(
                PositionStepLock.position_id == position_id
            )
            result = await self.db.execute(stmt)
            step_lock_state = result.scalar_one_or_none()
            
            if not step_lock_state:
                logger.warning(f"⚠️ 未找到Step Lock状态: position_id={position_id}")
                return None
            
            # 查询持仓信息
            stmt = select(Position).where(Position.id == position_id)
            result = await self.db.execute(stmt)
            position = result.scalar_one_or_none()
            
            if not position or not position.is_open:
                logger.debug(f"⏭️ 持仓已关闭，跳过检查: position_id={position_id}")
                return None
            
            # 重建档位列表
            levels = [
                StepLockLevel(
                    level=level_data["level"],
                    threshold_pct=level_data["threshold_pct"],
                    lock_pct=level_data["lock_pct"],
                    threshold_price=level_data["threshold_price"],
                    lock_price=level_data["lock_price"]
                )
                for level_data in step_lock_state.levels_config
            ]
            
            # 创建Step Lock管理器
            step_lock_manager = StepLockManager({"levels": []})  # 不需要重新计算
            
            # 检查是否触发新档位
            position_side = PositionSide.LONG if position.side == "LONG" else PositionSide.SHORT
            triggered, new_level, new_sl_price = step_lock_manager.check_level_triggered(
                current_price=current_price,
                levels=levels,
                current_level=step_lock_state.current_level,
                side=position_side
            )
            
            if triggered:
                old_level = step_lock_state.current_level
                
                # 更新状态
                step_lock_state.current_level = new_level
                step_lock_state.peak_price = current_price
                step_lock_state.last_check_time = datetime.utcnow()
                await self.db.commit()
                
                logger.info(
                    f"🔒 Step Lock触发: position_id={position_id} "
                    f"档位 {old_level} → {new_level} "
                    f"新止损价={new_sl_price:.2f} "
                    f"当前价={current_price:.2f}"
                )
                
                return {
                    "triggered": True,
                    "new_level": new_level,
                    "new_sl_price": new_sl_price,
                    "old_level": old_level,
                    "current_price": current_price
                }
            else:
                # 更新峰值价格（如果当前价格更优）
                if position_side == PositionSide.LONG:
                    if current_price > step_lock_state.peak_price:
                        step_lock_state.peak_price = current_price
                        await self.db.commit()
                        logger.debug(f"📈 更新峰值价格: {current_price:.2f}")
                else:
                    if current_price < step_lock_state.peak_price:
                        step_lock_state.peak_price = current_price
                        await self.db.commit()
                        logger.debug(f"📉 更新峰值价格: {current_price:.2f}")
                
                step_lock_state.last_check_time = datetime.utcnow()
                await self.db.commit()
                
                return None
            
        except Exception as e:
            logger.error(f"❌ Step Lock检查失败: {e}")
            return None
    
    async def get_step_lock_state(self, position_id: int) -> Optional[Dict]:
        """
        获取Step Lock状态
        
        Args:
            position_id: 持仓ID
        
        Returns:
            状态信息
        """
        try:
            stmt = select(PositionStepLock).where(
                PositionStepLock.position_id == position_id
            )
            result = await self.db.execute(stmt)
            step_lock_state = result.scalar_one_or_none()
            
            if not step_lock_state:
                return None
            
            return {
                "position_id": position_id,
                "current_level": step_lock_state.current_level,
                "peak_price": step_lock_state.peak_price,
                "levels_count": len(step_lock_state.levels_config),
                "last_check_time": step_lock_state.last_check_time
            }
            
        except Exception as e:
            logger.error(f"❌ 获取Step Lock状态失败: {e}")
            return None


# 全局单例
_step_lock_coordinator: Optional[StepLockCoordinator] = None


def get_step_lock_coordinator(db: AsyncSession) -> StepLockCoordinator:
    """获取Step Lock协调器实例"""
    return StepLockCoordinator(db)
