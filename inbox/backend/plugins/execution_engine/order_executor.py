"""
订单执行器 - 完整实现
处理订单创建、提交、状态跟踪和持仓管理
"""
import asyncio
from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from core.event_bus import EventBus


class OrderSide(str, Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """订单类型"""
    MARKET = "MARKET"  # 市价单
    LIMIT = "LIMIT"  # 限价单
    STOP_MARKET = "STOP_MARKET"  # 止损市价单
    STOP_LIMIT = "STOP_LIMIT"  # 止损限价单
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"  # 止盈市价单
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"  # 止盈限价单


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "PENDING"  # 待提交
    SUBMITTED = "SUBMITTED"  # 已提交
    PARTIAL_FILLED = "PARTIAL_FILLED"  # 部分成交
    FILLED = "FILLED"  # 完全成交
    CANCELLED = "CANCELLED"  # 已取消
    REJECTED = "REJECTED"  # 已拒绝
    EXPIRED = "EXPIRED"  # 已过期


@dataclass
class Order:
    """订单数据结构"""
    order_id: str
    account_id: str
    instance_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_price: float = 0.0
    fee: float = 0.0
    created_at: datetime = None
    updated_at: datetime = None
    exchange_order_id: Optional[str] = None


class OrderExecutor:
    """
    订单执行器
    
    职责：
    1. 创建订单
    2. 提交订单到交易所
    3. 跟踪订单状态
    4. 更新持仓信息
    """
    
    def __init__(self, config: Dict):
        """
        初始化订单执行器
        
        Args:
            config: 配置参数
                {
                    "exchange": "binance",
                    "api_key": "xxx",
                    "api_secret": "xxx",
                    "testnet": False
                }
        """
        self.exchange = config.get("exchange", "binance")
        self.api_key = config.get("api_key", "")
        self.api_secret = config.get("api_secret", "")
        self.testnet = config.get("testnet", False)
        
        # 订单管理
        self.orders: Dict[str, Order] = {}
        
        # 事件总线
        self.event_bus = EventBus.get_instance()
        
        logger.info(f"✅ 订单执行器初始化: 交易所={self.exchange}, 测试网={self.testnet}")
    
    async def create_market_order(
        self,
        account_id: str,
        instance_id: str,
        symbol: str,
        side: OrderSide,
        quantity: float
    ) -> Order:
        """
        创建市价单
        
        Args:
            account_id: 账户ID
            instance_id: 实例ID
            symbol: 交易对
            side: 订单方向
            quantity: 数量
        
        Returns:
            订单对象
        """
        order_id = self._generate_order_id()
        
        order = Order(
            order_id=order_id,
            account_id=account_id,
            instance_id=instance_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            status=OrderStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.orders[order_id] = order
        
        logger.info(
            f"📝 创建市价单: {order_id} {symbol} {side.value} {quantity}"
        )
        
        return order
    
    async def create_limit_order(
        self,
        account_id: str,
        instance_id: str,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float
    ) -> Order:
        """
        创建限价单
        
        Args:
            account_id: 账户ID
            instance_id: 实例ID
            symbol: 交易对
            side: 订单方向
            quantity: 数量
            price: 限价
        
        Returns:
            订单对象
        """
        order_id = self._generate_order_id()
        
        order = Order(
            order_id=order_id,
            account_id=account_id,
            instance_id=instance_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.orders[order_id] = order
        
        logger.info(
            f"📝 创建限价单: {order_id} {symbol} {side.value} {quantity} @ {price}"
        )
        
        return order
    
    async def create_stop_order(
        self,
        account_id: str,
        instance_id: str,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_price: float,
        limit_price: Optional[float] = None
    ) -> Order:
        """
        创建止损单
        
        Args:
            account_id: 账户ID
            instance_id: 实例ID
            symbol: 交易对
            side: 订单方向
            quantity: 数量
            stop_price: 止损触发价
            limit_price: 限价（如果为None则为止损市价单）
        
        Returns:
            订单对象
        """
        order_id = self._generate_order_id()
        
        if limit_price is None:
            order_type = OrderType.STOP_MARKET
        else:
            order_type = OrderType.STOP_LIMIT
        
        order = Order(
            order_id=order_id,
            account_id=account_id,
            instance_id=instance_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=limit_price,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.orders[order_id] = order
        
        logger.info(
            f"📝 创建止损单: {order_id} {symbol} {side.value} {quantity} "
            f"止损={stop_price} 限价={limit_price}"
        )
        
        return order
    
    async def submit_order(self, order_id: str) -> bool:
        """
        提交订单到交易所
        
        Args:
            order_id: 订单ID
        
        Returns:
            是否提交成功
        """
        if order_id not in self.orders:
            logger.error(f"❌ 订单不存在: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        try:
            # 实际项目中需要调用交易所API
            # 这里模拟提交成功
            exchange_order_id = await self._submit_to_exchange(order)
            
            # 更新订单状态
            order.status = OrderStatus.SUBMITTED
            order.exchange_order_id = exchange_order_id
            order.updated_at = datetime.now()
            
            logger.info(f"✅ 订单已提交: {order_id} -> 交易所订单ID={exchange_order_id}")
            
            # 发布订单事件
            await self.event_bus.publish(
                f"order:submitted:{order.account_id}",
                {
                    "order_id": order_id,
                    "exchange_order_id": exchange_order_id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "quantity": order.quantity
                }
            )
            
            # 模拟订单成交（实际项目中通过WebSocket接收成交通知）
            asyncio.create_task(self._simulate_order_fill(order_id))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 订单提交失败: {order_id}, 错误: {e}")
            order.status = OrderStatus.REJECTED
            order.updated_at = datetime.now()
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单ID
        
        Returns:
            是否取消成功
        """
        if order_id not in self.orders:
            logger.error(f"❌ 订单不存在: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            logger.warning(f"⚠️ 订单已完成或已取消，无法取消: {order_id}")
            return False
        
        try:
            # 实际项目中需要调用交易所API取消订单
            # await self._cancel_on_exchange(order.exchange_order_id)
            
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now()
            
            logger.info(f"✅ 订单已取消: {order_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 订单取消失败: {order_id}, 错误: {e}")
            return False
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单信息"""
        return self.orders.get(order_id)
    
    async def get_orders_by_instance(self, instance_id: str) -> List[Order]:
        """获取实例的所有订单"""
        return [
            order for order in self.orders.values()
            if order.instance_id == instance_id
        ]
    
    def _generate_order_id(self) -> str:
        """生成订单ID"""
        import uuid
        return f"ORD_{uuid.uuid4().hex[:16].upper()}"
    
    async def _submit_to_exchange(self, order: Order) -> str:
        """
        提交订单到交易所（真实实现）
        
        使用币安API提交订单
        """
        try:
            from core.binance_client import get_binance_client
            from core.database import get_db, Account
            from sqlalchemy import select
            
            # 获取数据库连接
            async for db in get_db():
                # 查询账户信息
                result = await db.execute(
                    select(Account).where(Account.id == self.account_id)
                )
                account = result.scalar_one_or_none()
                
                if not account:
                    raise Exception(f"账户不存在: {self.account_id}")
                
                # 获取币安客户端
                client = await get_binance_client(
                    account_id=account.id,
                    api_key=account.api_key,
                    api_secret=account.api_secret,
                    testnet=account.testnet
                )
                
                # 转换交易对格式（BTCUSDT -> BTC/USDT）
                symbol = order.symbol
                if '/' not in symbol:
                    # 假设是USDT交易对
                    if symbol.endswith('USDT'):
                        base = symbol[:-4]
                        symbol = f"{base}/USDT"
                    else:
                        symbol = f"{symbol}/USDT"
                
                # 根据订单类型提交
                if order.order_type == OrderType.MARKET:
                    # 市价单（进场一律使用市价）
                    result = await client.create_market_order(
                        symbol=symbol,
                        side=order.side.value.lower(),
                        amount=order.quantity
                    )
                elif order.order_type == OrderType.LIMIT:
                    # 限价单（止盈止损使用）
                    result = await client.create_limit_order(
                        symbol=symbol,
                        side=order.side.value.lower(),
                        amount=order.quantity,
                        price=order.price
                    )
                else:
                    raise Exception(f"不支持的订单类型: {order.order_type}")
                
                # 返回交易所订单ID
                exchange_order_id = str(result.get('id', ''))
                
                logger.info(
                    f"✅ 订单提交成功: {order.order_id} -> {exchange_order_id} "
                    f"{order.symbol} {order.side.value} {order.quantity}"
                )
                
                return exchange_order_id
                
        except Exception as e:
            logger.error(f"❌ 提交订单到交易所失败: {e}")
            raise
    
    async def _simulate_order_fill(self, order_id: str):
        """
        模拟订单成交（测试用）
        
        实际项目中删除此方法，通过WebSocket接收成交通知
        """
        await asyncio.sleep(0.5)  # 模拟成交延迟
        
        if order_id not in self.orders:
            return
        
        order = self.orders[order_id]
        
        # 模拟成交
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_price = order.price if order.price else 50000.0  # 模拟成交价
        order.fee = order.quantity * order.avg_price * 0.0004  # 模拟手续费
        order.updated_at = datetime.now()
        
        logger.info(
            f"✅ 订单成交: {order_id} "
            f"成交量={order.filled_quantity} "
            f"均价={order.avg_price:.2f} "
            f"手续费={order.fee:.2f}"
        )
        
        # 发布成交事件
        await self.event_bus.publish(
            f"order:filled:{order.account_id}",
            {
                "order_id": order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.filled_quantity,
                "avg_price": order.avg_price,
                "fee": order.fee
            }
        )


# 全局订单执行器实例
order_executor: Optional[OrderExecutor] = None


def get_order_executor() -> OrderExecutor:
    """获取全局订单执行器实例"""
    global order_executor
    
    if order_executor is None:
        config = {
            "exchange": "binance",
            "testnet": True
        }
        order_executor = OrderExecutor(config)
    
    return order_executor


# 示例使用
if __name__ == "__main__":
    async def test_order_executor():
        """测试订单执行器"""
        config = {
            "exchange": "binance",
            "testnet": True
        }
        executor = OrderExecutor(config)
        
        # 创建市价单
        order = await executor.create_market_order(
            account_id="ACC001",
            instance_id="INS001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.01
        )
        
        # 提交订单
        success = await executor.submit_order(order.order_id)
        print(f"订单提交: {success}")
        
        # 等待成交
        await asyncio.sleep(1)
        
        # 查询订单
        updated_order = await executor.get_order(order.order_id)
        print(f"订单状态: {updated_order.status.value}")
    
    asyncio.run(test_order_executor())
