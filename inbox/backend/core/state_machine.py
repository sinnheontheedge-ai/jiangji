"""
状态机管理系统

功能:
1. 定义状态枚举和转换规则
2. 验证状态转换的合法性
3. 记录状态转换历史
4. 支持分布式锁保证并发安全
5. 支持状态回滚和恢复
"""
import asyncio
from enum import Enum
from typing import Optional, List, Dict, Callable
from datetime import datetime
from loguru import logger
# import aioredis  # Using redis.asyncio instead
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from contextlib import asynccontextmanager


class InstanceState(str, Enum):
    """实例状态枚举"""
    CREATED = "created"       # 已创建（初始状态）
    STARTING = "starting"     # 启动中
    RUNNING = "running"       # 运行中
    STOPPING = "stopping"     # 停止中
    STOPPED = "stopped"       # 已停止
    ERROR = "error"           # 错误
    RESTARTING = "restarting" # 重启中
    PAUSED = "paused"         # 已暂停


class OrderState(str, Enum):
    """订单状态枚举"""
    CREATED = "created"       # 已创建
    PENDING = "pending"       # 待成交
    PARTIAL_FILLED = "partial_filled"  # 部分成交
    FILLED = "filled"         # 已成交
    CANCELLING = "cancelling" # 取消中
    CANCELLED = "cancelled"   # 已取消
    REJECTED = "rejected"     # 已拒绝
    EXPIRED = "expired"       # 已过期


class PositionState(str, Enum):
    """持仓状态枚举"""
    OPEN = "open"             # 持仓中
    CLOSING = "closing"       # 平仓中
    CLOSED = "closed"         # 已平仓


class StateTransitionError(Exception):
    """状态转换错误"""
    pass


class StateMachine:
    """状态机管理器"""
    
    # 实例状态转换规则
    INSTANCE_TRANSITIONS = {
        InstanceState.CREATED: [InstanceState.STARTING],
        InstanceState.STARTING: [InstanceState.RUNNING, InstanceState.ERROR],
        InstanceState.RUNNING: [
            InstanceState.STOPPING,
            InstanceState.RESTARTING,
            InstanceState.PAUSED,
            InstanceState.ERROR
        ],
        InstanceState.STOPPING: [InstanceState.STOPPED, InstanceState.ERROR],
        InstanceState.STOPPED: [InstanceState.STARTING],
        InstanceState.ERROR: [InstanceState.STARTING, InstanceState.STOPPED],
        InstanceState.RESTARTING: [InstanceState.RUNNING, InstanceState.ERROR],
        InstanceState.PAUSED: [InstanceState.RUNNING, InstanceState.STOPPING],
    }
    
    # 订单状态转换规则
    ORDER_TRANSITIONS = {
        OrderState.CREATED: [OrderState.PENDING, OrderState.REJECTED],
        OrderState.PENDING: [
            OrderState.PARTIAL_FILLED,
            OrderState.FILLED,
            OrderState.CANCELLING,
            OrderState.REJECTED,
            OrderState.EXPIRED
        ],
        OrderState.PARTIAL_FILLED: [
            OrderState.FILLED,
            OrderState.CANCELLING,
            OrderState.EXPIRED
        ],
        OrderState.FILLED: [],  # 终态
        OrderState.CANCELLING: [OrderState.CANCELLED, OrderState.FILLED],
        OrderState.CANCELLED: [],  # 终态
        OrderState.REJECTED: [],  # 终态
        OrderState.EXPIRED: [],  # 终态
    }
    
    # 持仓状态转换规则
    POSITION_TRANSITIONS = {
        PositionState.OPEN: [PositionState.CLOSING],
        PositionState.CLOSING: [PositionState.CLOSED, PositionState.OPEN],
        PositionState.CLOSED: [],  # 终态
    }
    
    def __init__(self, redis, db_session: AsyncSession):
        """
        初始化状态机
        
        参数:
        - redis: Redis连接（用于分布式锁）
        - db_session: 数据库会话
        """
        self.redis = redis
        self.db_session = db_session
        
        # 状态转换回调
        self.callbacks: Dict[str, List[Callable]] = {}
        
        logger.info("✅ 状态机管理器初始化完成")
    
    def can_transition(
        self,
        from_state: Enum,
        to_state: Enum,
        entity_type: str = "instance"
    ) -> bool:
        """
        检查是否可以转换状态
        
        参数:
        - from_state: 当前状态
        - to_state: 目标状态
        - entity_type: 实体类型（instance/order/position）
        
        返回: 是否可以转换
        """
        if entity_type == "instance":
            transitions = self.INSTANCE_TRANSITIONS
        elif entity_type == "order":
            transitions = self.ORDER_TRANSITIONS
        elif entity_type == "position":
            transitions = self.POSITION_TRANSITIONS
        else:
            raise ValueError(f"未知的实体类型: {entity_type}")
        
        allowed_states = transitions.get(from_state, [])
        return to_state in allowed_states
    
    @asynccontextmanager
    async def lock(self, entity_type: str, entity_id: int, timeout: int = 10):
        """
        分布式锁上下文管理器
        
        参数:
        - entity_type: 实体类型
        - entity_id: 实体ID
        - timeout: 超时时间（秒）
        """
        import uuid
        
        lock_key = f"state_lock:{entity_type}:{entity_id}"
        lock_value = str(uuid.uuid4())
        
        # 尝试获取锁
        acquired = await self.redis.set(
            lock_key,
            lock_value,
            ex=timeout,
            nx=True
        )
        
        if not acquired:
            raise StateTransitionError(
                f"无法获取状态锁: {entity_type}:{entity_id}（可能有其他操作正在进行）"
            )
        
        try:
            yield
        finally:
            # 释放锁（使用Lua脚本保证原子性）
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await self.redis.eval(lua_script, 1, lock_key, lock_value)
    
    async def transition(
        self,
        entity_type: str,
        entity_id: int,
        to_state: Enum,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """
        执行状态转换
        
        参数:
        - entity_type: 实体类型（instance/order/position）
        - entity_id: 实体ID
        - to_state: 目标状态
        - reason: 转换原因
        - metadata: 附加元数据
        
        抛出: StateTransitionError
        """
        async with self.lock(entity_type, entity_id):
            # 获取当前状态
            from_state = await self._get_current_state(entity_type, entity_id)
            
            # 验证状态转换
            if not self.can_transition(from_state, to_state, entity_type):
                raise StateTransitionError(
                    f"无效的状态转换: {entity_type}:{entity_id} "
                    f"{from_state.value} -> {to_state.value}"
                )
            
            # 记录状态转换历史
            await self._log_transition(
                entity_type,
                entity_id,
                from_state,
                to_state,
                reason,
                metadata
            )
            
            # 更新状态
            await self._update_state(entity_type, entity_id, to_state)
            
            # 触发回调
            await self._trigger_callbacks(
                entity_type,
                entity_id,
                from_state,
                to_state
            )
            
            logger.info(
                f"✅ 状态转换成功: {entity_type}:{entity_id} "
                f"{from_state.value} -> {to_state.value} "
                f"(原因: {reason or 'N/A'})"
            )
    
    async def _get_current_state(self, entity_type: str, entity_id: int) -> Enum:
        """获取当前状态"""
        if entity_type == "instance":
            from core.database import StrategyInstance
            result = await self.db_session.execute(
                select(StrategyInstance.status).where(
                    StrategyInstance.id == entity_id
                )
            )
            state_value = result.scalar_one_or_none()
            if state_value is None:
                raise ValueError(f"实例不存在: {entity_id}")
            return InstanceState(state_value)
        
        elif entity_type == "order":
            from core.database import Order
            result = await self.db_session.execute(
                select(Order.status).where(Order.id == entity_id)
            )
            state_value = result.scalar_one_or_none()
            if state_value is None:
                raise ValueError(f"订单不存在: {entity_id}")
            return OrderState(state_value)
        
        elif entity_type == "position":
            from core.database import Position
            result = await self.db_session.execute(
                select(Position.status).where(Position.id == entity_id)
            )
            state_value = result.scalar_one_or_none()
            if state_value is None:
                raise ValueError(f"持仓不存在: {entity_id}")
            return PositionState(state_value)
        
        else:
            raise ValueError(f"未知的实体类型: {entity_type}")
    
    async def _update_state(self, entity_type: str, entity_id: int, new_state: Enum):
        """更新状态"""
        if entity_type == "instance":
            from core.database import StrategyInstance
            await self.db_session.execute(
                f"UPDATE strategy_instances SET status = '{new_state.value}', "
                f"updated_at = NOW() WHERE id = {entity_id}"
            )
        
        elif entity_type == "order":
            from core.database import Order
            await self.db_session.execute(
                f"UPDATE orders SET status = '{new_state.value}', "
                f"updated_at = NOW() WHERE id = {entity_id}"
            )
        
        elif entity_type == "position":
            from core.database import Position
            await self.db_session.execute(
                f"UPDATE positions SET status = '{new_state.value}', "
                f"updated_at = NOW() WHERE id = {entity_id}"
            )
        
        await self.db_session.commit()
    
    async def _log_transition(
        self,
        entity_type: str,
        entity_id: int,
        from_state: Enum,
        to_state: Enum,
        reason: Optional[str],
        metadata: Optional[dict]
    ):
        """记录状态转换历史"""
        import json
        
        # 插入状态转换记录
        query = """
        INSERT INTO state_transitions
        (entity_type, entity_id, from_state, to_state, reason, metadata, created_at)
        VALUES (:entity_type, :entity_id, :from_state, :to_state, :reason, :metadata, NOW())
        """
        
        await self.db_session.execute(
            query,
            {
                'entity_type': entity_type,
                'entity_id': entity_id,
                'from_state': from_state.value,
                'to_state': to_state.value,
                'reason': reason,
                'metadata': json.dumps(metadata) if metadata else None
            }
        )
        await self.db_session.commit()
    
    async def get_transition_history(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 100
    ) -> List[dict]:
        """
        获取状态转换历史
        
        参数:
        - entity_type: 实体类型
        - entity_id: 实体ID
        - limit: 返回数量限制
        
        返回: 状态转换记录列表
        """
        query = """
        SELECT * FROM state_transitions
        WHERE entity_type = :entity_type AND entity_id = :entity_id
        ORDER BY created_at DESC
        LIMIT :limit
        """
        
        result = await self.db_session.execute(
            query,
            {
                'entity_type': entity_type,
                'entity_id': entity_id,
                'limit': limit
            }
        )
        
        return [dict(row) for row in result.fetchall()]
    
    def register_callback(
        self,
        entity_type: str,
        from_state: Enum,
        to_state: Enum,
        callback: Callable
    ):
        """
        注册状态转换回调
        
        参数:
        - entity_type: 实体类型
        - from_state: 源状态
        - to_state: 目标状态
        - callback: 回调函数
        """
        key = f"{entity_type}:{from_state.value}:{to_state.value}"
        if key not in self.callbacks:
            self.callbacks[key] = []
        self.callbacks[key].append(callback)
    
    async def _trigger_callbacks(
        self,
        entity_type: str,
        entity_id: int,
        from_state: Enum,
        to_state: Enum
    ):
        """触发状态转换回调"""
        key = f"{entity_type}:{from_state.value}:{to_state.value}"
        callbacks = self.callbacks.get(key, [])
        
        for callback in callbacks:
            try:
                await callback(entity_id, from_state, to_state)
            except Exception as e:
                logger.error(f"状态转换回调失败: {e}")


# 全局状态机实例
_state_machine: Optional[StateMachine] = None


def init_state_machine(redis, db_session: AsyncSession):
    """初始化全局状态机"""
    global _state_machine
    _state_machine = StateMachine(redis, db_session)
    return _state_machine


def get_state_machine() -> StateMachine:
    """获取全局状态机实例"""
    if _state_machine is None:
        raise RuntimeError("状态机未初始化，请先调用init_state_machine()")
    return _state_machine
