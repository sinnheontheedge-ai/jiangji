"""
订单监控器 - 监听订单成交并撤销剩余订单

职责：
1. 监听订单成交事件（WebSocket OnTick）
2. 订单成交后立即撤销该持仓的其他未成交订单
3. 监听持仓平仓事件（手动平仓）
4. 持仓平仓后立即撤销该持仓的所有未成交订单
5. 幂等性处理（防止重复撤单）
"""
import asyncio
from typing import Dict, Any, Optional
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.event_bus import EventBus
from core.database import Order, Position, get_db
from core.binance_client import BinanceClient


class OrderMonitor:
    """订单监控器"""
    
    def __init__(self):
        """初始化订单监控器"""
        self.event_bus = EventBus.get_instance()
        self.clients: Dict[int, BinanceClient] = {}  # account_id -> client
        
    async def start(self):
        """启动订单监控器"""
        # 订阅订单成交事件
        await self.event_bus.subscribe("order:filled:*", self._on_order_filled)
        
        # 订阅持仓平仓事件
        await self.event_bus.subscribe("position:closed:*", self._on_position_closed)
        
        logger.info("✅ 订单监控器已启动")
    
    def register_client(self, account_id: int, client: BinanceClient):
        """
        注册交易所客户端
        
        Args:
            account_id: 账户ID
            client: Binance客户端
        """
        self.clients[account_id] = client
        logger.debug(f"注册客户端: account_id={account_id}")
    
    async def _on_order_filled(self, channel: str, data: Dict[str, Any]):
        """
        处理订单成交事件
        
        Args:
            channel: 事件频道，如 "order:filled:12345"
            data: 订单数据
                {
                    "order_id": 12345,
                    "position_id": 67890,
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "status": "FILLED",
                    ...
                }
        """
        order_id = data.get("order_id")
        position_id = data.get("position_id")
        
        if not position_id:
            logger.warning(f"⚠️ 订单 {order_id} 没有关联持仓，跳过")
            return
        
        logger.info(f"📊 订单成交: order_id={order_id}, position_id={position_id}")
        
        # 撤销该持仓的其他未成交订单
        await self._cancel_remaining_orders(position_id, f"订单{order_id}成交")
    
    async def _on_position_closed(self, channel: str, data: Dict[str, Any]):
        """
        处理持仓平仓事件（手动平仓）
        
        Args:
            channel: 事件频道，如 "position:closed:67890"
            data: 持仓数据
                {
                    "position_id": 67890,
                    "symbol": "BTCUSDT",
                    "side": "LONG",
                    "quantity": 0,
                    ...
                }
        """
        position_id = data.get("position_id")
        
        if not position_id:
            logger.warning(f"⚠️ 持仓平仓事件缺少position_id，跳过")
            return
        
        logger.info(f"📊 持仓平仓: position_id={position_id}")
        
        # 撤销该持仓的所有未成交订单
        await self._cancel_remaining_orders(position_id, "持仓已平仓")
    
    async def _cancel_remaining_orders(self, position_id: int, reason: str):
        """
        撤销指定持仓的所有未成交订单（幂等）
        
        Args:
            position_id: 持仓ID
            reason: 撤单原因
        """
        async for db in get_db():
            try:
                # 查询该持仓的所有未成交订单
                result = await db.execute(
                    select(Order).where(
                        Order.position_id == position_id,
                        Order.status == "NEW"  # 只查询挂单中的订单
                    )
                )
                remaining_orders = result.scalars().all()
                
                if not remaining_orders:
                    logger.debug(f"ℹ️ 持仓 {position_id} 没有未成交订单")
                    return
                
                logger.info(f"🔄 开始撤销持仓 {position_id} 的 {len(remaining_orders)} 个未成交订单，原因: {reason}")
                
                # 获取持仓信息（用于获取account_id和symbol）
                position_result = await db.execute(
                    select(Position).where(Position.id == position_id)
                )
                position = position_result.scalar_one_or_none()
                
                if not position:
                    logger.error(f"❌ 持仓 {position_id} 不存在")
                    return
                
                # 获取交易所客户端
                client = self.clients.get(position.account_id)
                if not client:
                    logger.error(f"❌ 账户 {position.account_id} 的客户端未注册")
                    return
                
                # 逐个撤销订单
                for order in remaining_orders:
                    try:
                        # 调用交易所API撤销订单
                        await client.cancel_order(
                            symbol=order.symbol,
                            order_id=order.exchange_order_id
                        )
                        
                        # 更新数据库状态
                        order.status = "CANCELED"
                        await db.commit()
                        
                        logger.info(f"✅ 撤销订单成功: order_id={order.id}, exchange_order_id={order.exchange_order_id}")
                        
                    except Exception as e:
                        error_msg = str(e).lower()
                        
                        # 如果订单已经不存在（被其他监听器撤销或已成交），标记为CANCELED
                        if any(keyword in error_msg for keyword in [
                            "unknown order",
                            "order does not exist",
                            "already canceled",
                            "order not found"
                        ]):
                            logger.info(f"ℹ️ 订单已不存在: order_id={order.id}, exchange_order_id={order.exchange_order_id}")
                            order.status = "CANCELED"
                            await db.commit()
                        
                        # 其他错误（网络错误、API限流等）
                        else:
                            logger.error(f"❌ 撤销订单失败: order_id={order.id}, 错误: {e}")
                            # 不更新状态，留待下次重试
                            continue
                
                logger.info(f"✅ 持仓 {position_id} 的未成交订单撤销完成")
                
            except Exception as e:
                logger.error(f"❌ 撤销剩余订单失败: position_id={position_id}, 错误: {e}")
            
            finally:
                break  # 只执行一次


# 全局订单监控器实例
order_monitor = OrderMonitor()
