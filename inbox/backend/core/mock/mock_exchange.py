"""
Mock交易所实现
支持: 断网、超时、部分成交、重试、reduceOnly校验
用于无需真实Binance账号的测试和演示
"""
import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from decimal import Decimal
from loguru import logger
from datetime import datetime
import uuid


class MockExchangeError(Exception):
    """Mock交易所异常"""
    pass


class NetworkError(MockExchangeError):
    """网络错误"""
    pass


class TimeoutError(MockExchangeError):
    """超时错误"""
    pass


class MockExchange:
    """
    Mock交易所实现
    
    特性:
    1. 支持模拟断网、超时、部分成交
    2. 强制校验reduceOnly
    3. 支持clientOrderId幂等性
    4. 记录所有调用到JSONL日志
    """
    
    def __init__(
        self,
        testnet: bool = True,
        network_fail_rate: float = 0.0,
        timeout_rate: float = 0.0,
        partial_fill_rate: float = 0.0,
        log_file: Optional[str] = None
    ):
        """
        初始化Mock交易所
        
        Args:
            testnet: 是否为测试网
            network_fail_rate: 网络失败概率 (0.0-1.0)
            timeout_rate: 超时概率 (0.0-1.0)
            partial_fill_rate: 部分成交概率 (0.0-1.0)
            log_file: 日志文件路径
        """
        self.testnet = testnet
        self.network_fail_rate = network_fail_rate
        self.timeout_rate = timeout_rate
        self.partial_fill_rate = partial_fill_rate
        self.log_file = log_file or "logs/exchange_call.jsonl"
        
        # 内存数据库
        self.orders: Dict[str, Dict] = {}  # orderId -> order
        self.positions: Dict[str, Dict] = {}  # symbol -> position
        self.balance: Decimal = Decimal("10000.0")  # 初始余额
        self.client_order_ids: set = set()  # 已使用的clientOrderId
        
        # 价格模拟
        self.prices: Dict[str, Decimal] = {
            "BTC/USDT": Decimal("50000.0"),
            "ETH/USDT": Decimal("3000.0"),
            "BTCUSDT": Decimal("50000.0"),
            "ETHUSDT": Decimal("3000.0"),
        }
        
        logger.info(f"✅ MockExchange初始化: testnet={testnet}, 初始余额={self.balance}")
    
    def _log_call(self, method: str, params: Dict, result: Any, error: Optional[str] = None):
        """记录API调用到JSONL"""
        import json
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "params": params,
            "result": result if not error else None,
            "error": error,
            "balance_after": str(self.balance)
        }
        
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"❌ 写入日志失败: {e}")
    
    def _simulate_network_issues(self):
        """模拟网络问题"""
        if random.random() < self.network_fail_rate:
            raise NetworkError("模拟网络断开")
        
        if random.random() < self.timeout_rate:
            raise TimeoutError("模拟请求超时")
    
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        创建市价单
        
        Args:
            symbol: 交易对
            side: 方向 (buy/sell)
            amount: 数量
            params: 额外参数 (包含reduceOnly, newClientOrderId)
        
        Returns:
            订单信息
        """
        params = params or {}
        
        # 模拟网络问题
        self._simulate_network_issues()
        
        # P0强制: reduceOnly校验
        reduce_only = params.get('reduceOnly', False)
        client_order_id = params.get('newClientOrderId')
        
        # 幂等性检查
        if client_order_id:
            if client_order_id in self.client_order_ids:
                logger.warning(f"⚠️ 检测到重复clientOrderId: {client_order_id}, 返回已有订单")
                # 查找已有订单
                for order in self.orders.values():
                    if order.get('clientOrderId') == client_order_id:
                        self._log_call("create_market_order", {
                            "symbol": symbol,
                            "side": side,
                            "amount": amount,
                            "reduceOnly": reduce_only,
                            "clientOrderId": client_order_id
                        }, order, error="DUPLICATE_CLIENT_ORDER_ID")
                        return order
            else:
                self.client_order_ids.add(client_order_id)
        
        # reduceOnly强制校验
        if reduce_only:
            position = self.positions.get(symbol)
            if not position or position['quantity'] == 0:
                error_msg = f"reduceOnly订单失败: {symbol}无持仓"
                logger.error(f"❌ {error_msg}")
                self._log_call("create_market_order", {
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "reduceOnly": reduce_only,
                    "clientOrderId": client_order_id
                }, None, error=error_msg)
                raise MockExchangeError(error_msg)
            
            # 检查方向是否正确
            if position['side'] == 'LONG' and side.upper() != 'SELL':
                error_msg = f"reduceOnly订单方向错误: 持仓LONG必须SELL"
                logger.error(f"❌ {error_msg}")
                self._log_call("create_market_order", {
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "reduceOnly": reduce_only,
                    "clientOrderId": client_order_id
                }, None, error=error_msg)
                raise MockExchangeError(error_msg)
            
            if position['side'] == 'SHORT' and side.upper() != 'BUY':
                error_msg = f"reduceOnly订单方向错误: 持仓SHORT必须BUY"
                logger.error(f"❌ {error_msg}")
                self._log_call("create_market_order", {
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "reduceOnly": reduce_only,
                    "clientOrderId": client_order_id
                }, None, error=error_msg)
                raise MockExchangeError(error_msg)
        
        # 模拟部分成交
        filled_amount = amount
        if random.random() < self.partial_fill_rate:
            filled_amount = amount * random.uniform(0.5, 0.9)
            logger.warning(f"⚠️ 模拟部分成交: {filled_amount}/{amount}")
        
        # 创建订单
        order_id = str(uuid.uuid4())
        price = self.prices.get(symbol, Decimal("1.0"))
        
        order = {
            "id": order_id,
            "clientOrderId": client_order_id,
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "amount": amount,
            "filled": filled_amount,
            "remaining": amount - filled_amount,
            "price": float(price),
            "cost": float(price * Decimal(str(filled_amount))),
            "status": "closed" if filled_amount == amount else "open",
            "reduceOnly": reduce_only,
            "timestamp": int(time.time() * 1000),
            "datetime": datetime.now().isoformat()
        }
        
        self.orders[order_id] = order
        
        # 更新持仓
        self._update_position(symbol, side, filled_amount, price, reduce_only)
        
        # 记录日志
        self._log_call("create_market_order", {
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "reduceOnly": reduce_only,
            "clientOrderId": client_order_id,
            "reason": params.get('reason', 'unknown'),
            "source": params.get('source', 'unknown')
        }, order)
        
        logger.info(f"✅ Mock订单创建成功: {order_id} {symbol} {side} {filled_amount}/{amount}")
        
        return order
    
    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: Optional[Dict] = None
    ) -> Dict:
        """创建限价单"""
        params = params or {}
        
        # 模拟网络问题
        self._simulate_network_issues()
        
        reduce_only = params.get('reduceOnly', False)
        client_order_id = params.get('newClientOrderId')
        
        # 幂等性检查
        if client_order_id and client_order_id in self.client_order_ids:
            logger.warning(f"⚠️ 检测到重复clientOrderId: {client_order_id}")
            for order in self.orders.values():
                if order.get('clientOrderId') == client_order_id:
                    return order
        
        if client_order_id:
            self.client_order_ids.add(client_order_id)
        
        # reduceOnly校验
        if reduce_only:
            position = self.positions.get(symbol)
            if not position or position['quantity'] == 0:
                raise MockExchangeError(f"reduceOnly订单失败: {symbol}无持仓")
        
        order_id = str(uuid.uuid4())
        
        order = {
            "id": order_id,
            "clientOrderId": client_order_id,
            "symbol": symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "amount": amount,
            "filled": 0,
            "remaining": amount,
            "price": price,
            "cost": 0,
            "status": "open",
            "reduceOnly": reduce_only,
            "timestamp": int(time.time() * 1000),
            "datetime": datetime.now().isoformat()
        }
        
        self.orders[order_id] = order
        
        self._log_call("create_limit_order", {
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "reduceOnly": reduce_only,
            "clientOrderId": client_order_id
        }, order)
        
        logger.info(f"✅ Mock限价单创建成功: {order_id}")
        
        return order
    
    def _update_position(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: Decimal,
        reduce_only: bool
    ):
        """更新持仓"""
        if symbol not in self.positions:
            self.positions[symbol] = {
                "symbol": symbol,
                "side": None,
                "quantity": 0,
                "entry_price": 0,
                "unrealized_pnl": 0
            }
        
        position = self.positions[symbol]
        
        if reduce_only:
            # 平仓逻辑
            if side.upper() == 'SELL':
                position['quantity'] -= amount
            else:
                position['quantity'] += amount
            
            if abs(position['quantity']) < 0.0001:
                position['quantity'] = 0
                position['side'] = None
        else:
            # 开仓逻辑
            if side.upper() == 'BUY':
                position['side'] = 'LONG'
                position['quantity'] += amount
            else:
                position['side'] = 'SHORT'
                position['quantity'] -= amount
            
            position['entry_price'] = float(price)
    
    async def fetch_balance(self) -> Dict:
        """获取余额"""
        return {
            "USDT": {
                "free": float(self.balance),
                "used": 0,
                "total": float(self.balance)
            }
        }
    
    async def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[Dict]:
        """获取持仓"""
        positions = []
        for symbol, pos in self.positions.items():
            if symbols and symbol not in symbols:
                continue
            if pos['quantity'] != 0:
                positions.append({
                    "symbol": symbol,
                    "side": pos['side'],
                    "contracts": abs(pos['quantity']),
                    "contractSize": 1,
                    "entryPrice": pos['entry_price'],
                    "markPrice": float(self.prices.get(symbol, Decimal("1.0"))),
                    "unrealizedPnl": pos['unrealized_pnl'],
                    "percentage": 0,
                    "leverage": 10,
                    "marginType": "cross"
                })
        return positions
    
    async def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """设置杠杆"""
        logger.info(f"✅ Mock设置杠杆: {symbol} {leverage}x")
        return {"leverage": leverage, "symbol": symbol}
    
    async def set_margin_mode(self, symbol: str, margin_mode: str) -> Dict:
        """设置保证金模式"""
        logger.info(f"✅ Mock设置保证金模式: {symbol} {margin_mode}")
        return {"marginMode": margin_mode, "symbol": symbol}
    
    async def transfer(
        self,
        currency: str,
        amount: float,
        from_account: str,
        to_account: str
    ) -> Dict:
        """资金划转"""
        logger.info(f"✅ Mock资金划转: {amount} {currency} from {from_account} to {to_account}")
        
        transfer_id = str(uuid.uuid4())
        
        result = {
            "id": transfer_id,
            "currency": currency,
            "amount": amount,
            "fromAccount": from_account,
            "toAccount": to_account,
            "status": "ok",
            "timestamp": int(time.time() * 1000)
        }
        
        self._log_call("transfer", {
            "currency": currency,
            "amount": amount,
            "from": from_account,
            "to": to_account
        }, result)
        
        return result
    
    def set_price(self, symbol: str, price: float):
        """设置模拟价格（用于测试）"""
        self.prices[symbol] = Decimal(str(price))
        logger.debug(f"📊 设置Mock价格: {symbol} = {price}")
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """获取单个持仓"""
        return self.positions.get(symbol)
    
    def reset(self):
        """重置Mock交易所状态"""
        self.orders.clear()
        self.positions.clear()
        self.client_order_ids.clear()
        self.balance = Decimal("10000.0")
        logger.info("🔄 MockExchange已重置")
