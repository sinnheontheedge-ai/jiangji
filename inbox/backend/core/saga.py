"""
Saga模式 - 分布式事务补偿机制

功能:
1. 编排多步骤事务
2. 自动补偿（回滚）失败的事务
3. 记录事务执行历史
4. 支持事务恢复
5. 保证最终一致性
"""
from typing import List, Callable, Optional, Any, Dict
from enum import Enum
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
import json


class SagaStatus(str, Enum):
    """Saga状态"""
    PENDING = "pending"        # 待执行
    EXECUTING = "executing"    # 执行中
    COMPLETED = "completed"    # 已完成
    COMPENSATING = "compensating"  # 补偿中
    COMPENSATED = "compensated"    # 已补偿
    FAILED = "failed"          # 失败


class SagaStep:
    """Saga步骤"""
    
    def __init__(
        self,
        name: str,
        action: Callable,
        compensate: Callable,
        description: Optional[str] = None
    ):
        """
        初始化Saga步骤
        
        参数:
        - name: 步骤名称
        - action: 执行函数
        - compensate: 补偿函数（回滚）
        - description: 步骤描述
        """
        self.name = name
        self.action = action
        self.compensate = compensate
        self.description = description or name


class SagaOrchestrator:
    """
    Saga编排器
    
    工作流程:
    1. 按顺序执行所有步骤
    2. 记录每个步骤的执行结果
    3. 如果某步骤失败，逆序执行补偿操作
    4. 保证最终一致性
    """
    
    def __init__(
        self,
        saga_id: str,
        db_session: Optional[AsyncSession] = None
    ):
        """
        初始化Saga编排器
        
        参数:
        - saga_id: Saga唯一标识
        - db_session: 数据库会话（用于记录历史）
        """
        self.saga_id = saga_id
        self.db_session = db_session
        
        self.steps: List[SagaStep] = []
        self.executed_steps: List[tuple] = []  # (step, result)
        self.status = SagaStatus.PENDING
        
        logger.info(f"✅ Saga编排器初始化: {saga_id}")
    
    def add_step(self, step: SagaStep):
        """
        添加步骤
        
        参数:
        - step: Saga步骤
        """
        self.steps.append(step)
        logger.debug(f"添加Saga步骤: {step.name}")
    
    async def execute(self) -> bool:
        """
        执行Saga
        
        返回: 是否成功
        """
        self.status = SagaStatus.EXECUTING
        await self._log_saga_start()
        
        try:
            # 按顺序执行所有步骤
            for i, step in enumerate(self.steps, 1):
                logger.info(
                    f"执行Saga步骤 [{i}/{len(self.steps)}]: {step.name}"
                )
                
                try:
                    # 执行步骤
                    result = await step.action()
                    
                    # 记录执行结果
                    self.executed_steps.append((step, result))
                    
                    # 记录步骤日志
                    await self._log_step_success(step, result)
                    
                    logger.info(f"✅ 步骤执行成功: {step.name}")
                
                except Exception as e:
                    logger.error(f"❌ 步骤执行失败: {step.name} - {e}")
                    
                    # 记录步骤失败
                    await self._log_step_failure(step, str(e))
                    
                    # 开始补偿
                    await self.compensate()
                    
                    raise
            
            # 所有步骤执行成功
            self.status = SagaStatus.COMPLETED
            await self._log_saga_complete()
            
            logger.info(f"🎉 Saga执行成功: {self.saga_id}")
            return True
        
        except Exception as e:
            self.status = SagaStatus.FAILED
            await self._log_saga_failure(str(e))
            
            logger.error(f"❌ Saga执行失败: {self.saga_id} - {e}")
            raise
    
    async def compensate(self):
        """
        补偿操作（回滚）
        
        逆序执行已执行步骤的补偿函数
        """
        self.status = SagaStatus.COMPENSATING
        await self._log_saga_compensate_start()
        
        logger.warning(f"🔄 开始补偿操作: {self.saga_id}")
        
        # 逆序执行补偿
        for step, result in reversed(self.executed_steps):
            try:
                logger.info(f"补偿步骤: {step.name}")
                
                # 执行补偿
                await step.compensate(result)
                
                # 记录补偿成功
                await self._log_step_compensate_success(step)
                
                logger.info(f"✅ 补偿成功: {step.name}")
            
            except Exception as e:
                logger.error(f"❌ 补偿失败: {step.name} - {e}")
                
                # 记录补偿失败（但继续补偿其他步骤）
                await self._log_step_compensate_failure(step, str(e))
        
        self.status = SagaStatus.COMPENSATED
        await self._log_saga_compensate_complete()
        
        logger.info(f"✅ 补偿完成: {self.saga_id}")
    
    async def _log_saga_start(self):
        """记录Saga开始"""
        if not self.db_session:
            return
        
        query = """
        INSERT INTO saga_logs
        (saga_id, status, step_count, created_at)
        VALUES (:saga_id, :status, :step_count, NOW())
        """
        
        await self.db_session.execute(
            query,
            {
                'saga_id': self.saga_id,
                'status': self.status.value,
                'step_count': len(self.steps)
            }
        )
        await self.db_session.commit()
    
    async def _log_saga_complete(self):
        """记录Saga完成"""
        if not self.db_session:
            return
        
        query = """
        UPDATE saga_logs
        SET status = :status, completed_at = NOW()
        WHERE saga_id = :saga_id
        """
        
        await self.db_session.execute(
            query,
            {
                'saga_id': self.saga_id,
                'status': self.status.value
            }
        )
        await self.db_session.commit()
    
    async def _log_saga_failure(self, error: str):
        """记录Saga失败"""
        if not self.db_session:
            return
        
        query = """
        UPDATE saga_logs
        SET status = :status, error = :error, failed_at = NOW()
        WHERE saga_id = :saga_id
        """
        
        await self.db_session.execute(
            query,
            {
                'saga_id': self.saga_id,
                'status': self.status.value,
                'error': error
            }
        )
        await self.db_session.commit()
    
    async def _log_saga_compensate_start(self):
        """记录Saga补偿开始"""
        if not self.db_session:
            return
        
        query = """
        UPDATE saga_logs
        SET status = :status, compensate_started_at = NOW()
        WHERE saga_id = :saga_id
        """
        
        await self.db_session.execute(
            query,
            {
                'saga_id': self.saga_id,
                'status': self.status.value
            }
        )
        await self.db_session.commit()
    
    async def _log_saga_compensate_complete(self):
        """记录Saga补偿完成"""
        if not self.db_session:
            return
        
        query = """
        UPDATE saga_logs
        SET status = :status, compensate_completed_at = NOW()
        WHERE saga_id = :saga_id
        """
        
        await self.db_session.execute(
            query,
            {
                'saga_id': self.saga_id,
                'status': self.status.value
            }
        )
        await self.db_session.commit()
    
    async def _log_step_success(self, step: SagaStep, result: Any):
        """记录步骤成功"""
        if not self.db_session:
            return
        
        query = """
        INSERT INTO saga_step_logs
        (saga_id, step_name, status, result, created_at)
        VALUES (:saga_id, :step_name, 'success', :result, NOW())
        """
        
        await self.db_session.execute(
            query,
            {
                'saga_id': self.saga_id,
                'step_name': step.name,
                'result': json.dumps(result) if result else None
            }
        )
        await self.db_session.commit()
    
    async def _log_step_failure(self, step: SagaStep, error: str):
        """记录步骤失败"""
        if not self.db_session:
            return
        
        query = """
        INSERT INTO saga_step_logs
        (saga_id, step_name, status, error, created_at)
        VALUES (:saga_id, :step_name, 'failed', :error, NOW())
        """
        
        await self.db_session.execute(
            query,
            {
                'saga_id': self.saga_id,
                'step_name': step.name,
                'error': error
            }
        )
        await self.db_session.commit()
    
    async def _log_step_compensate_success(self, step: SagaStep):
        """记录步骤补偿成功"""
        if not self.db_session:
            return
        
        query = """
        INSERT INTO saga_step_logs
        (saga_id, step_name, status, created_at)
        VALUES (:saga_id, :step_name, 'compensated', NOW())
        """
        
        await self.db_session.execute(
            query,
            {
                'saga_id': self.saga_id,
                'step_name': step.name
            }
        )
        await self.db_session.commit()
    
    async def _log_step_compensate_failure(self, step: SagaStep, error: str):
        """记录步骤补偿失败"""
        if not self.db_session:
            return
        
        query = """
        INSERT INTO saga_step_logs
        (saga_id, step_name, status, error, created_at)
        VALUES (:saga_id, :step_name, 'compensate_failed', :error, NOW())
        """
        
        await self.db_session.execute(
            query,
            {
                'saga_id': self.saga_id,
                'step_name': step.name,
                'error': error
            }
        )
        await self.db_session.commit()


# 使用示例
async def example_create_order_saga():
    """示例：创建订单的Saga流程"""
    saga = SagaOrchestrator(saga_id="order_123")
    
    # 步骤1：创建数据库订单
    saga.add_step(SagaStep(
        name="create_db_order",
        action=lambda: create_db_order({'symbol': 'BTCUSDT', 'quantity': 0.01}),
        compensate=lambda result: delete_db_order(result['order_id']),
        description="创建数据库订单"
    ))
    
    # 步骤2：调用交易所API下单
    saga.add_step(SagaStep(
        name="create_exchange_order",
        action=lambda: create_exchange_order({'symbol': 'BTCUSDT', 'quantity': 0.01}),
        compensate=lambda result: cancel_exchange_order(result['exchange_order_id']),
        description="交易所下单"
    ))
    
    # 步骤3：扣除保证金
    saga.add_step(SagaStep(
        name="deduct_margin",
        action=lambda: deduct_margin({'amount': 100}),
        compensate=lambda result: refund_margin(result['margin_amount']),
        description="扣除保证金"
    ))
    
    # 步骤4：发送通知
    saga.add_step(SagaStep(
        name="send_notification",
        action=lambda: send_notification({'message': '订单已创建'}),
        compensate=lambda result: None,  # 通知无需补偿
        description="发送通知"
    ))
    
    # 执行Saga
    await saga.execute()


# 占位函数（实际应该替换为真实实现）
async def create_db_order(data): return {'order_id': 123}
async def delete_db_order(order_id): pass
async def create_exchange_order(data): return {'exchange_order_id': 'abc123'}
async def cancel_exchange_order(exchange_order_id): pass
async def deduct_margin(data): return {'margin_amount': 100}
async def refund_margin(amount): pass
async def send_notification(data): pass
