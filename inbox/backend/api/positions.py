"""
持仓管理API
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database import get_db, Position

logger = logging.getLogger(__name__)

router = APIRouter()


class PositionListResponse(BaseModel):
    """持仓列表响应"""
    items: list
    total: int


@router.get("/positions", response_model=PositionListResponse)
async def list_positions(
    symbol: Optional[str] = Query(None, description="交易对过滤"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取持仓列表
    
    参数:
    - symbol: 交易对 (如BTCUSDT)
    """
    try:
        query = select(Position)
        
        # 交易对过滤
        if symbol:
            query = query.where(Position.symbol == symbol)
        
        # 按时间倒序
        query = query.order_by(Position.created_at.desc())
        
        result = await db.execute(query)
        positions = result.scalars().all()
        
        # 转换为字典
        items = []
        for pos in positions:
            items.append({
                'id': pos.id,
                'instance_id': pos.instance_id,
                'symbol': pos.symbol,
                'side': pos.side,
                'quantity': float(pos.quantity),
                'entry_price': float(pos.entry_price),
                'current_price': float(pos.current_price) if pos.current_price else float(pos.entry_price),
                'unrealized_pnl': float(pos.unrealized_pnl) if pos.unrealized_pnl else 0,
                'leverage': pos.leverage,
                'created_at': pos.created_at.isoformat() if pos.created_at else None,
                'updated_at': pos.updated_at.isoformat() if pos.updated_at else None,
            })
        
        return PositionListResponse(items=items, total=len(items))
        
    except Exception as e:
        logger.error(f"获取持仓列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/{position_id}")
async def get_position(position_id: int, db: AsyncSession = Depends(get_db)):
    """获取持仓详情"""
    try:
        result = await db.execute(
            select(Position).where(Position.id == position_id)
        )
        pos = result.scalar_one_or_none()
        
        if not pos:
            raise HTTPException(status_code=404, detail="持仓不存在")
        
        return {
            'id': pos.id,
            'instance_id': pos.instance_id,
            'symbol': pos.symbol,
            'side': pos.side,
            'quantity': float(pos.quantity),
            'entry_price': float(pos.entry_price),
            'current_price': float(pos.current_price) if pos.current_price else float(pos.entry_price),
            'unrealized_pnl': float(pos.unrealized_pnl) if pos.unrealized_pnl else 0,
            'leverage': pos.leverage,
            'created_at': pos.created_at.isoformat() if pos.created_at else None,
            'updated_at': pos.updated_at.isoformat() if pos.updated_at else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取持仓详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/positions/{position_id}/close")
async def close_position(position_id: int, db: AsyncSession = Depends(get_db)):
    """平仓"""
    try:
        result = await db.execute(
            select(Position).where(Position.id == position_id)
        )
        pos = result.scalar_one_or_none()
        
        if not pos:
            raise HTTPException(status_code=404, detail="持仓不存在")
        
        # 修复: 调用交易所API平仓
        try:
            # 获取实例和账户信息
            from core.database import Instance, Account
            from core.binance_client import get_binance_client
            
            instance_result = await db.execute(
                select(Instance).where(Instance.id == pos.instance_id)
            )
            instance = instance_result.scalar_one_or_none()
            
            if not instance:
                raise ValueError("实例不存在")
            
            account_result = await db.execute(
                select(Account).where(Account.id == instance.account_id)
            )
            account = account_result.scalar_one_or_none()
            
            if not account:
                raise ValueError("账户不存在")
            
            # 创建交易所客户端
            client = await get_binance_client(
                account_id=account.id,
                api_key=account.api_key,
                api_secret=account.api_secret,
                testnet=account.testnet,
                proxy=account.proxy_config
            )
            
            # P0修复: 调用交易所API平仓 - 必须使用clientOrderId和reduce_only=True
            side = 'sell' if pos.side == 'LONG' else 'buy'
            
            # 生成幂等性键
            import uuid
            import time
            client_order_id = f"close_{pos.id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            logger.info(
                f"📝 准备平仓: position_id={pos.id}, symbol={pos.symbol}, "
                f"side={side}, quantity={abs(pos.quantity)}, clientOrderId={client_order_id}"
            )
            
            order_result = await client.create_market_order(
                symbol=pos.symbol,
                side=side,
                amount=abs(pos.quantity),
                reduce_only=True,  # P0修复: 平仓必须设置reduceOnly=True
                client_order_id=client_order_id  # P0修复: 幂等性保障
            )
            
            logger.info(f"✅ 交易所平仓成功: {pos.symbol}, 订单ID={order_result.get('orderId')}")
            
            # 更新数据库持仓状态
            pos.is_open = False  # 修复: 使用is_open字段标记已平仓
            pos.quantity = 0  # 清零持仓数量
            await db.commit()
            
            logger.info(f"✅ 持仓已平仓: {position_id} {pos.symbol}")
            
        except Exception as close_error:
            logger.error(f"❌ 平仓失败: {close_error}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"平仓失败: {str(close_error)}"
            )
        
        return {'message': '持仓已平仓', 'position_id': position_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"平仓失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
