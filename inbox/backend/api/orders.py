"""
订单管理API
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database import get_db, Order

logger = logging.getLogger(__name__)

router = APIRouter()


class OrderListResponse(BaseModel):
    """订单列表响应"""
    items: list
    total: int


@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    status: Optional[str] = Query(None, description="订单状态过滤"),
    symbol: Optional[str] = Query(None, description="交易对过滤"),
    limit: Optional[int] = Query(100, description="返回数量限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取订单列表
    
    参数:
    - status: 订单状态 (pending/filled/cancelled/rejected)
    - symbol: 交易对 (如BTCUSDT)
    - limit: 返回数量限制
    """
    try:
        query = select(Order)
        
        # 状态过滤
        if status and status != 'all':
            query = query.where(Order.status == status)
        
        # 交易对过滤
        if symbol:
            query = query.where(Order.symbol == symbol)
        
        # 按时间倒序
        query = query.order_by(Order.created_at.desc())
        
        # 限制数量
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        orders = result.scalars().all()
        
        # 转换为字典
        items = []
        for order in orders:
            items.append({
                'id': order.id,
                'instance_id': order.instance_id,
                'symbol': order.symbol,
                'side': order.side,
                'order_type': order.order_type,
                'quantity': float(order.quantity),
                'price': float(order.price) if order.price else None,
                'status': order.status,
                'exchange_order_id': order.exchange_order_id,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'updated_at': order.updated_at.isoformat() if order.updated_at else None,
            })
        
        return OrderListResponse(items=items, total=len(items))
        
    except Exception as e:
        logger.error(f"获取订单列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}")
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """获取订单详情"""
    try:
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        return {
            'id': order.id,
            'instance_id': order.instance_id,
            'symbol': order.symbol,
            'side': order.side,
            'order_type': order.order_type,
            'quantity': float(order.quantity),
            'price': float(order.price) if order.price else None,
            'status': order.status,
            'exchange_order_id': order.exchange_order_id,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'updated_at': order.updated_at.isoformat() if order.updated_at else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取订单详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """取消订单"""
    try:
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        if order.status != 'pending':
            raise HTTPException(status_code=400, detail=f"订单状态为{order.status}，无法取消")
        
        # 修复: 调用交易所API取消订单
        try:
            # 获取实例和账户信息
            from core.database import Instance, Account
            from core.binance_client import get_binance_client
            
            instance_result = await db.execute(
                select(Instance).where(Instance.id == order.instance_id)
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
            
            # 调用交易所API取消订单
            if order.exchange_order_id:
                await client.cancel_order(
                    symbol=order.symbol,
                    order_id=order.exchange_order_id
                )
                logger.info(f"✅ 交易所订单已取消: {order.exchange_order_id}")
            
            # 更新数据库订单状态
            order.status = 'cancelled'
            await db.commit()
            
            logger.info(f"✅ 订单已取消: {order_id}")
            
        except Exception as cancel_error:
            logger.error(f"❌ 取消交易所订单失败: {cancel_error}")
            # 即使交易所取消失败，也更新数据库状态
            order.status = 'cancelled'
            await db.commit()
            raise HTTPException(
                status_code=500, 
                detail=f"取消订单失败: {str(cancel_error)}"
            )
        
        return {'message': '订单已取消', 'order_id': order_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消订单失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
