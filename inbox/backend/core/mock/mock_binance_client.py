"""
Mock版BinanceClient
用于替代真实BinanceClient进行测试
"""
from typing import Dict, List, Optional
from loguru import logger
from .mock_exchange import MockExchange


class MockBinanceClient:
    """
    Mock版币安客户端
    完全兼容BinanceClient接口
    """
    
    def __init__(
        self,
        api_key: str = "mock_key",
        api_secret: str = "mock_secret",
        testnet: bool = True,
        proxy: Optional[Dict] = None,
        network_fail_rate: float = 0.0,
        timeout_rate: float = 0.0,
        partial_fill_rate: float = 0.0,
        log_file: Optional[str] = None
    ):
        """
        初始化Mock客户端
        
        Args:
            api_key: API密钥（Mock不使用）
            api_secret: API密钥（Mock不使用）
            testnet: 是否测试网
            proxy: 代理配置（Mock不使用）
            network_fail_rate: 网络失败概率
            timeout_rate: 超时概率
            partial_fill_rate: 部分成交概率
            log_file: 日志文件路径
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.proxy = proxy
        
        # 使用MockExchange作为底层
        self.exchange = MockExchange(
            testnet=testnet,
            network_fail_rate=network_fail_rate,
            timeout_rate=timeout_rate,
            partial_fill_rate=partial_fill_rate,
            log_file=log_file
        )
        
        logger.info(f"✅ MockBinanceClient初始化完成 (testnet={testnet})")
    
    async def get_balance(self, currency: str = "USDT") -> float:
        """获取余额"""
        balance_info = await self.exchange.fetch_balance()
        return balance_info.get(currency, {}).get("free", 0.0)
    
    async def get_positions(self, symbols: Optional[List[str]] = None) -> List[Dict]:
        """获取持仓列表"""
        return await self.exchange.fetch_positions(symbols)
    
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        reduce_only: bool = False,
        client_order_id: Optional[str] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """创建市价单"""
        params = params or {}
        params['reduceOnly'] = reduce_only
        if client_order_id:
            params['newClientOrderId'] = client_order_id
        
        return await self.exchange.create_market_order(
            symbol=symbol,
            side=side,
            amount=amount,
            params=params
        )
    
    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        reduce_only: bool = False,
        client_order_id: Optional[str] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """创建限价单"""
        params = params or {}
        params['reduceOnly'] = reduce_only
        if client_order_id:
            params['newClientOrderId'] = client_order_id
        
        return await self.exchange.create_limit_order(
            symbol=symbol,
            side=side,
            amount=amount,
            price=price,
            params=params
        )
    
    async def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """设置杠杆"""
        return await self.exchange.set_leverage(symbol, leverage)
    
    async def set_position_mode(self, symbol: str, hedge: bool = False) -> Dict:
        """设置持仓模式"""
        mode = "hedge" if hedge else "one-way"
        return await self.exchange.set_margin_mode(symbol, mode)
    
    async def transfer_between_accounts(
        self,
        currency: str,
        amount: float,
        from_account: str,
        to_account: str
    ) -> Dict:
        """账户间划转"""
        return await self.exchange.transfer(
            currency=currency,
            amount=amount,
            from_account=from_account,
            to_account=to_account
        )
    
    async def get_ticker(self, symbol: str) -> Dict:
        """获取ticker"""
        price = self.exchange.prices.get(symbol, 0.0)
        return {
            "symbol": symbol,
            "last": float(price),
            "bid": float(price * 0.999),
            "ask": float(price * 1.001),
            "timestamp": None
        }
    
    async def close(self):
        """关闭客户端"""
        logger.info("👋 MockBinanceClient已关闭")
    
    def set_price(self, symbol: str, price: float):
        """设置模拟价格（测试用）"""
        self.exchange.set_price(symbol, price)
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """获取单个持仓（测试用）"""
        return self.exchange.get_position(symbol)
    
    def reset(self):
        """重置状态（测试用）"""
        self.exchange.reset()
