"""
系统管理API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger
from core.database import get_db, Account, Strategy, Instance, Order, Position

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "message": "系统运行正常"
    }


@router.get("/status")
async def system_status():
    """系统状态"""
    return {
        "status": "running",
        "version": "1.0.0",
        "components": {
            "event_bus": "running",
            "database": "connected",
            "strategy_manager": "running"
        }
    }


@router.get("/stats")
async def system_stats(db: AsyncSession = Depends(get_db)):
    """系统统计信息"""
    try:
        # 统计各类数据
        total_accounts = await db.scalar(select(func.count()).select_from(Account))
        total_strategies = await db.scalar(select(func.count()).select_from(Strategy))
        total_instances = await db.scalar(select(func.count()).select_from(Instance))
        
        # 统计运行中的实例
        active_instances = await db.scalar(
            select(func.count()).select_from(Instance).where(Instance.status == 'RUNNING')
        )
        
        total_orders = await db.scalar(select(func.count()).select_from(Order))
        
        # 统计持仓 (注意: Position表没有is_open字段,根据实际情况调整)
        open_positions = await db.scalar(select(func.count()).select_from(Position))
        
        # 计算总盈亏
        result = await db.execute(select(Position))
        positions = result.scalars().all()
        total_pnl = sum(float(pos.unrealized_pnl or 0) for pos in positions)
        
        return {
            "accounts": total_accounts or 0,
            "strategies": total_strategies or 0,
            "instances": total_instances or 0,
            "active_instances": active_instances or 0,
            "orders": total_orders or 0,
            "positions": open_positions or 0,
            "total_pnl": total_pnl
        }
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        return {
            "accounts": 0,
            "strategies": 0,
            "instances": 0,
            "active_instances": 0,
            "orders": 0,
            "positions": 0,
            "total_pnl": 0.0
        }
