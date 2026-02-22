"""
币安API客户端封装
提供账户查询、订单操作等功能
"""
import ccxt.async_support as ccxt
from typing import Dict, Optional, List
from loguru import logger
from decimal import Decimal


class BinanceClient:
    """币安API客户端"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False, proxy: Optional[Dict] = None):
        """
        初始化币安客户端
        
        Args:
            api_key: API密钥
            api_secret: API密钥
            testnet: 是否使用测试网
            proxy: 代理配置，格式: {'host': '127.0.0.1', 'port': 7890}
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.proxy = proxy
        
        # 构建代理配置
        proxies = None
        if proxy and 'host' in proxy and 'port' in proxy:
            proxy_url = f"http://{proxy['host']}:{proxy['port']}"
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            logger.info(f"🌐 使用代理: {proxy_url}")
        
        # 初始化交易所实例
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # 使用合约交易
                'adjustForTimeDifference': True
            },
            'proxies': proxies  # 添加代理配置
        })
        
        # 设置测试网
        if testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info("🔧 使用币安测试网")
        
        logger.info(f"✅ 币安客户端初始化完成 (testnet={testnet})")
    
    async def get_account_balance(self) -> Dict:
        """
        获取账户余额
        
        Returns:
            {
                'total_balance': 总资产(USDT),
                'available_balance': 可用余额(USDT),
                'margin_balance': 保证金余额(USDT),
                'unrealized_pnl': 未实现盈亏(USDT),
                'positions': [持仓列表]
            }
        """
        try:
            # 获取账户信息
            balance = await self.exchange.fetch_balance()
            
            # 获取合约账户信息
            if 'info' in balance and 'assets' in balance['info']:
                # 币安合约账户结构
                usdt_asset = None
                for asset in balance['info']['assets']:
                    if asset['asset'] == 'USDT':
                        usdt_asset = asset
                        break
                
                if usdt_asset:
                    total_balance = float(usdt_asset.get('walletBalance', 0))
                    available_balance = float(usdt_asset.get('availableBalance', 0))
                    margin_balance = float(usdt_asset.get('marginBalance', 0))
                    unrealized_pnl = float(usdt_asset.get('unrealizedProfit', 0))
                else:
                    # 如果没有USDT资产，返回0
                    total_balance = 0
                    available_balance = 0
                    margin_balance = 0
                    unrealized_pnl = 0
            else:
                # 备用方案：使用标准余额结构
                total_balance = float(balance.get('USDT', {}).get('total', 0))
                available_balance = float(balance.get('USDT', {}).get('free', 0))
                margin_balance = total_balance
                unrealized_pnl = 0
            
            # 获取持仓信息
            positions = await self.get_positions()
            
            result = {
                'total_balance': round(total_balance, 2),
                'available_balance': round(available_balance, 2),
                'margin_balance': round(margin_balance, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'positions': positions
            }
            
            logger.info(
                f"✅ 获取账户余额成功: "
                f"总资产={result['total_balance']} USDT, "
                f"可用={result['available_balance']} USDT, "
                f"未实现盈亏={result['unrealized_pnl']} USDT"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 获取账户余额失败: {e}")
            raise
    
    async def get_positions(self) -> List[Dict]:
        """
        获取持仓列表
        
        Returns:
            [
                {
                    'symbol': 交易对,
                    'side': 方向(long/short),
                    'size': 持仓数量,
                    'entry_price': 开仓价格,
                    'mark_price': 标记价格,
                    'liquidation_price': 强平价格,
                    'unrealized_pnl': 未实现盈亏,
                    'margin': 保证金
                }
            ]
        """
        try:
            positions = await self.exchange.fetch_positions()
            
            # 过滤出有持仓的交易对
            active_positions = []
            for pos in positions:
                if pos.get('contracts', 0) > 0:  # 有持仓
                    active_positions.append({
                        'symbol': pos.get('symbol', ''),
                        'side': pos.get('side', ''),
                        'size': float(pos.get('contracts', 0)),
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'liquidation_price': float(pos.get('liquidationPrice', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'margin': float(pos.get('initialMargin', 0))
                    })
            
            return active_positions
            
        except Exception as e:
            logger.error(f"❌ 获取持仓列表失败: {e}")
            return []
    
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        reduce_only: bool = False,
        client_order_id: Optional[str] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        创建市价单
        
        Args:
            symbol: 交易对，如 "BTC/USDT"
            side: 方向，"buy" 或 "sell"
            amount: 数量
            reduce_only: 是否仅减仓（平仓订单必须为True）
            client_order_id: 客户端订单ID（幂等性保障）
            params: 额外参数
        
        Returns:
            订单信息
        """
        try:
            # 合并参数
            order_params = params or {}
            
            # P0修复: 幂等性保障 - 必须使用clientOrderId
            if not client_order_id:
                import uuid
                client_order_id = f"order_{uuid.uuid4().hex[:16]}"
                logger.warning(f"⚠️ 未提供clientOrderId，自动生成: {client_order_id}")
            
            order_params['newClientOrderId'] = client_order_id
            logger.info(f"🔑 幂等性保障: clientOrderId={client_order_id}")
            
            # P0修复: 如果是平仓订单，强制设置reduceOnly=True
            if reduce_only:
                order_params['reduceOnly'] = True
                logger.info(f"🔒 平仓订单强制reduceOnly: {symbol} {side} {amount}, reduceOnly=True")
            else:
                # 开仓订单明确记录
                logger.info(f"📈 开仓订单: {symbol} {side} {amount}, reduceOnly=False")
            
            # 校验最小下单量
            await self._validate_order_amount(symbol, amount)
            
            # 创建订单
            logger.info(
                f"📝 准备下单: {symbol} {side} {amount} "
                f"reduceOnly={reduce_only} params={order_params}"
            )
            
            order = await self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount,
                params=order_params
            )
            
            logger.info(
                f"✅ 创建市价单成功: {symbol} {side} {amount} "
                f"订单ID={order.get('id')} reduceOnly={reduce_only}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"❌ 创建市价单失败: {symbol} {side} {amount} - {e}")
            raise
    
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
        """
        创建限价单
        
        Args:
            symbol: 交易对
            side: 方向
            amount: 数量
            price: 价格
            reduce_only: 是否仅减仓（平仓订单必须为True）
            client_order_id: 客户端订单ID
            params: 额外参数
        
        Returns:
            订单信息
        """
        try:
            order_params = params or {}
            
            # P0修复: 幂等性保障 - 必须使用clientOrderId
            if not client_order_id:
                import uuid
                client_order_id = f"order_{uuid.uuid4().hex[:16]}"
                logger.warning(f"⚠️ 未提供clientOrderId，自动生成: {client_order_id}")
            
            order_params['newClientOrderId'] = client_order_id
            logger.info(f"🔑 幂等性保障: clientOrderId={client_order_id}")
            
            # P0修复: 如果是平仓订单，强制设置reduceOnly=True
            if reduce_only:
                order_params['reduceOnly'] = True
                logger.info(f"🔒 平仓订单强制reduceOnly: {symbol} {side} {amount} @ {price}, reduceOnly=True")
            else:
                logger.info(f"📈 开仓订单: {symbol} {side} {amount} @ {price}, reduceOnly=False")
            
            order = await self.exchange.create_limit_order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                params=order_params
            )
            
            logger.info(
                f"✅ 创建限价单成功: {symbol} {side} {amount} @ {price} "
                f"订单ID={order.get('id')} reduceOnly={reduce_only}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"❌ 创建限价单失败: {e}")
            raise
    
    async def create_stop_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        reduce_only: bool = False,
        client_order_id: Optional[str] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        创建止损市价单
        
        Args:
            symbol: 交易对
            side: 方向
            amount: 数量
            stop_price: 止损价格
            reduce_only: 是否仅减仓（平仓订单必须为True）
            client_order_id: 客户端订单ID
            params: 额外参数
        
        Returns:
            订单信息
        """
        try:
            order_params = params or {}
            
            # P0修复: 幂等性保障 - 必须使用clientOrderId
            if not client_order_id:
                import uuid
                client_order_id = f"stop_{uuid.uuid4().hex[:16]}"
                logger.warning(f"⚠️ 未提供clientOrderId，自动生成: {client_order_id}")
            
            order_params['newClientOrderId'] = client_order_id
            order_params['stopPrice'] = stop_price
            logger.info(f"🔑 幂等性保障: clientOrderId={client_order_id}")
            
            # P0修复: 止损订单强制设置reduceOnly=True
            if reduce_only:
                order_params['reduceOnly'] = True
                logger.info(f"🔒 止损订单强制reduceOnly: {symbol} {side} {amount} stopPrice={stop_price}, reduceOnly=True")
            else:
                logger.warning(f"⚠️ 止损订单未设置reduceOnly: {symbol} {side} {amount}")
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side=side,
                amount=amount,
                params=order_params
            )
            
            logger.info(
                f"✅ 创建止损市价单成功: {symbol} {side} {amount} stopPrice={stop_price} "
                f"订单ID={order.get('id')} reduceOnly={reduce_only}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"❌ 创建止损市价单失败: {e}")
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            symbol: 交易对
        
        Returns:
            是否成功
        """
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"✅ 取消订单成功: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 取消订单失败: {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict:
        """
        查询订单状态
        
        Args:
            order_id: 订单ID
            symbol: 交易对
        
        Returns:
            订单信息
        """
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
            
        except Exception as e:
            logger.error(f"❌ 查询订单状态失败: {e}")
            raise
    
    async def fetch_historical_klines(self, symbol: str, timeframe: str, limit: int, since: Optional[int] = None) -> List[Dict]:
        """
        获取历史K线数据
        
        Args:
            symbol: 交易对，如 'BTC/USDT'
            timeframe: 时间周期，如 '1m', '5m', '1h', '1d'
            limit: 获取数量
            since: 开始时间戳（毫秒），可选
            
        Returns:
            历史K线数据列表
        """
        try:
            if since:
                logger.info(f"⏳ 正在为 {symbol} 获取自 {since} 以来的 {limit} 根 {timeframe} 历史K线...")
            else:
                logger.info(f"⏳ 正在为 {symbol} 获取最近 {limit} 根 {timeframe} 历史K线...")
            
            # 🔴 ccxt的fetch_ohlcv支持since参数
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            
            klines = [
                {
                    "timestamp": int(row[0]),  # 使用毫秒时间戳
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5])
                }
                for row in ohlcv
            ]
            logger.info(f"✅ 成功获取 {len(klines)} 根历史K线.")
            return klines
        except Exception as e:
            logger.error(f"❌ 获取历史K线失败: {e}")
            return []
    
    async def _validate_order_amount(self, symbol: str, amount: float) -> float:
        """
        校验订单数量是否符合交易所规则
        
        Args:
            symbol: 交易对
            amount: 数量
        
        Returns:
            调整后的数量
        """
        try:
            # 获取市场信息
            market = await self.exchange.fetch_market(symbol)
            
            # 检查最小下单量
            min_amount = market['limits']['amount']['min']
            if amount < min_amount:
                raise ValueError(
                    f"❌ 下单量{amount}小于最小值{min_amount}"
                )
            
            # 检查精度
            precision = market['precision']['amount']
            rounded_amount = round(amount, precision)
            if rounded_amount != amount:
                logger.warning(
                    f"⚠️ 下单量精度调整: {amount} → {rounded_amount}"
                )
                amount = rounded_amount
            
            logger.debug(f"✅ 订单数量校验通过: {symbol} {amount}")
            return amount
            
        except Exception as e:
            logger.error(f"❌ 校验订单数量失败: {e}")
            raise
    
    async def transfer_between_accounts(
        self,
        asset: str,
        amount: float,
        from_account: str,
        to_account: str
    ) -> Dict:
        """
        账户间转账
        
        Args:
            asset: 资产类型，如 'USDT'
            amount: 转账金额
            from_account: 源账户类型 ('SPOT' 或 'FUTURES')
            to_account: 目标账户类型 ('SPOT' 或 'FUTURES')
        
        Returns:
            转账结果
        """
        try:
            # 币安转账类型映射
            type_mapping = {
                'SPOT': 'MAIN_UMFUTURE',  # 现货 -> U本位合约
                'FUTURES': 'UMFUTURE_MAIN'  # U本位合约 -> 现货
            }
            
            transfer_type = None
            if from_account == 'SPOT' and to_account == 'FUTURES':
                transfer_type = type_mapping['SPOT']
            elif from_account == 'FUTURES' and to_account == 'SPOT':
                transfer_type = type_mapping['FUTURES']
            else:
                raise ValueError(f"不支持的转账类型: {from_account} -> {to_account}")
            
            # 调用币安API进行转账
            result = await self.exchange.sapi_post_asset_transfer({
                'type': transfer_type,
                'asset': asset,
                'amount': amount
            })
            
            logger.info(f"✅ 转账成功: {amount} {asset} ({from_account} -> {to_account})")
            return result
            
        except Exception as e:
            logger.error(f"❌ 转账失败: {e}")
            raise
    
    async def close(self):
        """关闭客户端"""
        try:
            await self.exchange.close()
            logger.info("👋 币安客户端已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭币安客户端失败: {e}")


# 全局客户端缓存
_clients: Dict[int, BinanceClient] = {}


async def get_binance_client(account_id: int, api_key: str, api_secret: str, testnet: bool = False, proxy: Optional[Dict] = None) -> BinanceClient:
    """
    获取币安客户端（带缓存）
    
    Args:
        account_id: 账户ID
        api_key: API密钥
        api_secret: API密钥
        testnet: 是否测试网
        proxy: 代理配置
    
    Returns:
        币安客户端实例
    """
    if account_id not in _clients:
        _clients[account_id] = BinanceClient(api_key, api_secret, testnet, proxy)
    
    return _clients[account_id]


async def close_all_clients():
    """关闭所有客户端"""
    for client in _clients.values():
        await client.close()
    _clients.clear()
