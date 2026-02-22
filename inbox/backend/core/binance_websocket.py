"""
币安WebSocket客户端
用于接收实时K线和Tick数据
"""
import asyncio
import json
import websockets
from typing import Dict, Set, Callable, Optional
from datetime import datetime
from loguru import logger

# 🔴 为数据完整性检查器添加必要的导入
from core.strategy_manager import strategy_manager
from core.binance_client import BinanceClient


class BinanceWebSocket:
    """币安WebSocket客户端"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = False, proxy: Optional[Dict] = None):
        """
        初始化WebSocket客户端
        
        Args:
            api_key: API密钥（用户数据流需要）
            api_secret: API密钥（用户数据流需要）
            testnet: 是否使用测试网
            proxy: 代理配置，格式: {'host': '127.0.0.1', 'port': 7890}
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.proxy = proxy
        
        # 构建代理URL
        self.proxy_url = None
        if proxy and 'host' in proxy and 'port' in proxy:
            self.proxy_url = f"http://{proxy['host']}:{proxy['port']}"
            logger.info(f"🌐 WebSocket将使用代理: {self.proxy_url}")
        
        # WebSocket URL
        if testnet:
            self.ws_url = "wss://stream.binancefuture.com/ws"  # 合约测试网
            self.api_base_url = "https://testnet.binancefuture.com"
        else:
            self.ws_url = "wss://fstream.binance.com/ws"  # 合约主网
            self.api_base_url = "https://fapi.binance.com"
        
        # 连接状态
        self.ws = None
        self.user_ws = None  # 用户数据流连接
        self.running = False
        self.reconnect_interval = 5
        
        # 订阅管理
        self.subscriptions: Set[str] = set()
        
        # 回调函数
        self.kline_callback: Optional[Callable] = None
        self.tick_callback: Optional[Callable] = None
        self.account_update_callback: Optional[Callable] = None
        self.position_update_callback: Optional[Callable] = None
        self.order_update_callback: Optional[Callable] = None
        
        # 用户数据流
        self.listen_key: Optional[str] = None
        self.listen_key_task: Optional[asyncio.Task] = None
        
        logger.info(f"✅ 币安WebSocket初始化完成 (testnet={testnet})")
    
    def set_kline_callback(self, callback: Callable):
        """设置K线数据回调函数"""
        self.kline_callback = callback
    
    def set_tick_callback(self, callback: Callable):
        """设置Tick数据回调函数"""
        self.tick_callback = callback
    
    def set_account_update_callback(self, callback: Callable):
        """设置账户更新回调函数"""
        self.account_update_callback = callback
    
    def set_position_update_callback(self, callback: Callable):
        """设置持仓更新回调函数"""
        self.position_update_callback = callback
    
    def set_order_update_callback(self, callback: Callable):
        """设置订单更新回调函数"""
        self.order_update_callback = callback
    
    async def connect(self):
        """连接WebSocket"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.running = True
            logger.info(f"✅ WebSocket连接成功: {self.ws_url}")
            
            # 启动消息接收循环
            asyncio.create_task(self._receive_loop())
            
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e}")
            raise
    
    async def disconnect(self):
        """断开WebSocket"""
        self.running = False
        
        # 停止listen key保活
        if self.listen_key_task:
            self.listen_key_task.cancel()
        
        # 关闭市场数据流
        if self.ws:
            await self.ws.close()
            logger.info("👋 市场数据流已断开")
        
        # 关闭用户数据流
        if self.user_ws:
            await self.user_ws.close()
            logger.info("👋 用户数据流已断开")
    
    async def subscribe_kline(self, symbol: str, interval: str):
        """
        订阅K线数据
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            interval: 时间周期，如 "1m", "5m", "15m", "1h", "4h", "1d"
        """
        try:
            # 转换为小写（币安要求）
            symbol = symbol.lower()
            
            # 构造订阅消息
            stream = f"{symbol}@kline_{interval}"
            
            if stream in self.subscriptions:
                logger.debug(f"已订阅K线: {symbol} {interval}")
                return
            
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [stream],
                "id": len(self.subscriptions) + 1
            }
            
            # 发送订阅请求
            if self.ws:
                await self.ws.send(json.dumps(subscribe_msg))
                self.subscriptions.add(stream)
                logger.info(f"📊 订阅K线成功: {symbol} {interval}")
            else:
                logger.error("❌ WebSocket未连接，无法订阅")
                
        except Exception as e:
            logger.error(f"❌ 订阅K线失败: {e}")
    
    async def subscribe_ticker(self, symbol: str):
        """
        订阅Ticker数据（最新价格）
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
        """
        try:
            symbol = symbol.lower()
            stream = f"{symbol}@ticker"
            
            if stream in self.subscriptions:
                logger.debug(f"已订阅Ticker: {symbol}")
                return
            
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [stream],
                "id": len(self.subscriptions) + 1
            }
            
            if self.ws:
                await self.ws.send(json.dumps(subscribe_msg))
                self.subscriptions.add(stream)
                logger.info(f"📈 订阅Ticker成功: {symbol}")
            else:
                logger.error("❌ WebSocket未连接，无法订阅")
                
        except Exception as e:
            logger.error(f"❌ 订阅Ticker失败: {e}")
    
    async def unsubscribe(self, stream: str):
        """取消订阅"""
        try:
            if stream not in self.subscriptions:
                return
            
            unsubscribe_msg = {
                "method": "UNSUBSCRIBE",
                "params": [stream],
                "id": len(self.subscriptions) + 1000
            }
            
            if self.ws:
                await self.ws.send(json.dumps(unsubscribe_msg))
                self.subscriptions.remove(stream)
                logger.info(f"🔕 取消订阅: {stream}")
                
        except Exception as e:
            logger.error(f"❌ 取消订阅失败: {e}")
    
    async def _receive_loop(self):
        """接收消息循环"""
        try:
            while self.running:
                try:
                    message = await self.ws.recv()
                    data = json.loads(message)
                    
                    # 处理不同类型的消息
                    if 'e' in data:  # 事件类型
                        event_type = data['e']
                        
                        if event_type == 'kline':
                            # K线数据
                            await self._handle_kline(data)
                        elif event_type == '24hrTicker':
                            # Ticker数据
                            await self._handle_ticker(data)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("⚠️ WebSocket连接断开，尝试重连...")
                    await self._reconnect()
                except Exception as e:
                    logger.error(f"❌ 接收消息失败: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"❌ 接收循环异常: {e}")
    
    async def _reconnect(self):
        """重新连接"""
        while self.running:
            try:
                logger.info(f"🔄 {self.reconnect_interval}秒后重连...")
                await asyncio.sleep(self.reconnect_interval)
                
                # 重新连接
                self.ws = await websockets.connect(self.ws_url)
                logger.info("✅ WebSocket重连成功")
                
                # --- 🔴 核心修改：在重新订阅前进行数据完整性检查 ---
                await self.data_integrity_checker()
                # --- 🔴 修改结束 ---
                
                # 重新订阅
                for stream in list(self.subscriptions):
                    subscribe_msg = {
                        "method": "SUBSCRIBE",
                        "params": [stream],
                        "id": 1
                    }
                    await self.ws.send(json.dumps(subscribe_msg))
                    logger.info(f"🔄 重新订阅: {stream}")
                
                break
                
            except Exception as e:
                logger.error(f"❌ 重连失败: {e}")
    
    async def data_integrity_checker(self):
        """
        数据完整性检查器，用于在重连后补齐数据
        
        流程：
        1. 遍历所有策略实例
        2. 获取每个策略最后一次处理的K线时间戳
        3. 通过REST API获取自该时间戳以来的所有K线
        4. 将这些“丢失”的K线重新喂给对应的策略实例
        """
        logger.info("🛡️ 开始数据完整性检查...")
        
        # 临时的REST客户端
        rest_client = BinanceClient(self.api_key, self.api_secret, self.testnet)
        
        try:
            for instance_id, strategy in strategy_manager.instances.items():
                last_ts = strategy.state.get("last_kline_timestamp", 0)
                if last_ts == 0:
                    logger.debug(f"实例 {instance_id}: 没有历史时间戳，跳过")
                    continue
                
                # 获取当前时间，并计算需要获取的K线数量
                now_ts = int(datetime.now().timestamp() * 1000)
                time_diff_ms = now_ts - last_ts
                
                # 根据timeframe计算limit
                timeframe = strategy.timeframe
                timeframe_ms = self._timeframe_to_ms(timeframe)
                
                if timeframe_ms == 0:
                    logger.warning(f"实例 {instance_id}: 无法识别的timeframe '{timeframe}'，跳过")
                    continue
                
                # 计算需要获取的K线数量（+1以确保完整覆盖）
                limit = int(time_diff_ms / timeframe_ms) + 1
                
                if limit > 0:
                    logger.info(f"实例 {instance_id}: 发现数据空窗期，尝试补齐 {limit} 根K线...")
                    
                    # 通过REST API获取丢失的K线
                    symbol = strategy.symbol
                    missed_klines = await rest_client.fetch_historical_klines(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=limit,
                        since=last_ts  # 🔴 使用since参数指定开始时间
                    )
                    
                    # 将丢失的K线依次喂给策略
                    补齐计数 = 0
                    for kline in missed_klines:
                        # 确保不处理重复数据
                        if kline["timestamp"] > last_ts:
                            strategy.on_kline(kline)
                            logger.debug(f"补齐数据: {kline['timestamp']}")
                            补齐计数 += 1
                    
                    logger.info(f"实例 {instance_id}: 成功补齐 {补齐计数} 根K线")
                else:
                    logger.debug(f"实例 {instance_id}: 数据完整，无需补齐")
        
        except Exception as e:
            logger.error(f"❌ 数据完整性检查失败: {e}")
        finally:
            await rest_client.close()
            logger.info("🛡️ 数据完整性检查完成")
    
    def _timeframe_to_ms(self, timeframe: str) -> int:
        """
        将timeframe字符串转换为毫秒
        
        Args:
            timeframe: 时间周期，如 '1m', '5m', '15m', '1h', '4h', '1d'
        
        Returns:
            毫秒数，如果无法识别则返回0
        """
        timeframe_map = {
            '1m': 60 * 1000,
            '3m': 3 * 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '30m': 30 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '2h': 2 * 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '6h': 6 * 60 * 60 * 1000,
            '8h': 8 * 60 * 60 * 1000,
            '12h': 12 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
            '3d': 3 * 24 * 60 * 60 * 1000,
            '1w': 7 * 24 * 60 * 60 * 1000,
            '1M': 30 * 24 * 60 * 60 * 1000,  # 近似值
        }
        return timeframe_map.get(timeframe, 0)
    
    async def _handle_kline(self, data: Dict):
        """
        处理K线数据
        
        数据格式:
        {
            "e": "kline",
            "E": 1638747660000,
            "s": "BTCUSDT",
            "k": {
                "t": 1638747600000,  # 开盘时间
                "T": 1638747659999,  # 收盘时间
                "s": "BTCUSDT",      # 交易对
                "i": "1m",           # 周期
                "o": "50000.00",     # 开盘价
                "c": "50100.00",     # 收盘价
                "h": "50200.00",     # 最高价
                "l": "49900.00",     # 最低价
                "v": "100.5",        # 成交量
                "x": false           # 是否完成
            }
        }
        """
        try:
            kline = data['k']
            
            # 转换为标准格式
            kline_data = {
                'symbol': kline['s'],
                'interval': kline['i'],
                'timestamp': kline['t'],
                'open': float(kline['o']),
                'high': float(kline['h']),
                'low': float(kline['l']),
                'close': float(kline['c']),
                'volume': float(kline['v']),
                'is_closed': kline['x']
            }
            
            # 调用回调函数
            if self.kline_callback:
                await self.kline_callback(kline_data)
            
        except Exception as e:
            logger.error(f"❌ 处理K线数据失败: {e}")
    
    async def _handle_ticker(self, data: Dict):
        """
        处理Ticker数据
        
        数据格式:
        {
            "e": "24hrTicker",
            "E": 1638747660000,
            "s": "BTCUSDT",
            "c": "50000.00",  # 最新价
            "v": "10000.5"    # 成交量
        }
        """
        try:
            ticker_data = {
                'symbol': data['s'],
                'price': float(data['c']),
                'volume': float(data['v']),
                'timestamp': data['E']
            }
            
            # 调用回调函数
            if self.tick_callback:
                await self.tick_callback(ticker_data)
            
        except Exception as e:
            logger.error(f"❌ 处理Ticker数据失败: {e}")
    
    # ==================== 用户数据流 ====================
    
    async def subscribe_user_data_stream(self):
        """
        订阅用户数据流
        
        接收:
        - ACCOUNT_UPDATE: 账户余额更新
        - ORDER_TRADE_UPDATE: 订单更新
        """
        if not self.api_key:
            logger.error("❌ 未提供API密钥，无法订阅用户数据流")
            return
        
        try:
            # 1. 获取listen key
            await self._create_listen_key()
            
            # 2. 连接WebSocket
            user_ws_url = f"{self.ws_url.replace('/ws', '')}/ws/{self.listen_key}"
            logger.info(f"📡 连接用户数据流: {user_ws_url}")
            
            # 3. 启动连接任务
            asyncio.create_task(self._maintain_user_data_stream(user_ws_url))
            
            # 4. 启动listen key保活任务
            self.listen_key_task = asyncio.create_task(self._keep_alive_listen_key())
            
            logger.info("✅ 用户数据流订阅成功")
            
        except Exception as e:
            logger.error(f"❌ 订阅用户数据流失败: {e}")
            raise
    
    async def _create_listen_key(self):
        """创廻listen key"""
        import httpx
        
        url = f"{self.api_base_url}/fapi/v1/listenKey"
        headers = {"X-MBX-APIKEY": self.api_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.listen_key = data["listenKey"]
            logger.info(f"✅ 创廻listen key: {self.listen_key}")
    
    async def _keep_alive_listen_key(self):
        """保活listen key (每30分钟)"""
        import httpx
        
        while self.running:
            try:
                await asyncio.sleep(30 * 60)  # 30分钟
                
                url = f"{self.api_base_url}/fapi/v1/listenKey"
                headers = {"X-MBX-APIKEY": self.api_key}
                
                async with httpx.AsyncClient() as client:
                    response = await client.put(url, headers=headers)
                    response.raise_for_status()
                    logger.info("✅ listen key保活成功")
                    
            except Exception as e:
                logger.error(f"❌ listen key保活失败: {e}")
    
    async def _maintain_user_data_stream(self, ws_url: str):
        """维护用户数据流连接（自动重连）"""
        retry_count = 0
        max_retries = 10
        
        while self.running:
            try:
                async with websockets.connect(ws_url) as ws:
                    self.user_ws = ws
                    logger.info("✅ 用户数据流连接成功")
                    retry_count = 0
                    
                    # 接收消息
                    async for message in ws:
                        await self._handle_user_data_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️ 用户数据流连接关闭")
                self.user_ws = None
                
                # 重连
                if self.running and retry_count < max_retries:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 60)
                    logger.info(f"🔄 {wait_time}秒后重连 (尝试 {retry_count}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                else:
                    break
                    
            except Exception as e:
                logger.error(f"❌ 用户数据流连接错误: {e}")
                self.user_ws = None
                
                if self.running and retry_count < max_retries:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 60)
                    await asyncio.sleep(wait_time)
                else:
                    break
    
    async def _handle_user_data_message(self, message: str):
        """处理用户数据流消息"""
        try:
            data = json.loads(message)
            event_type = data.get("e")
            
            if event_type == "ACCOUNT_UPDATE":
                # 账户更新
                await self._handle_account_update(data)
                
            elif event_type == "ORDER_TRADE_UPDATE":
                # 订单更新
                await self._handle_order_update(data)
                
        except Exception as e:
            logger.error(f"❌ 处理用户数据消息失败: {e}")
    
    async def _handle_account_update(self, data: dict):
        """处理账户更新"""
        try:
            account_data = data.get("a", {})
            
            # 余额更新
            balances = account_data.get("B", [])
            for balance in balances:
                asset = balance.get("a")
                wallet_balance = float(balance.get("wb", 0))
                cross_wallet_balance = float(balance.get("cw", 0))
                
                logger.info(f"💰 余额更新: {asset} 钱包={wallet_balance}, 合约={cross_wallet_balance}")
                
                # 调用回调
                if self.account_update_callback:
                    await self.account_update_callback({
                        "asset": asset,
                        "wallet_balance": wallet_balance,
                        "cross_wallet_balance": cross_wallet_balance,
                        "timestamp": data.get("E")
                    })
            
            # 持仓更新
            positions = account_data.get("P", [])
            for position in positions:
                symbol = position.get("s")
                position_amount = float(position.get("pa", 0))
                entry_price = float(position.get("ep", 0))
                unrealized_pnl = float(position.get("up", 0))
                
                # 只处理有持仓的
                if position_amount != 0:
                    logger.info(f"📊 持仓更新: {symbol} 数量={position_amount}, 入场价={entry_price}, 未实现盈亏={unrealized_pnl}")
                    
                    # 调用回调
                    if self.position_update_callback:
                        await self.position_update_callback({
                            "symbol": symbol,
                            "position_amount": position_amount,
                            "entry_price": entry_price,
                            "unrealized_pnl": unrealized_pnl,
                            "position_side": position.get("ps"),
                            "timestamp": data.get("E")
                        })
                    
        except Exception as e:
            logger.error(f"❌ 处理账户更新失败: {e}")
    
    async def _handle_order_update(self, data: dict):
        """处理订单更新"""
        try:
            order = data.get("o", {})
            
            symbol = order.get("s")
            order_id = order.get("i")
            order_status = order.get("X")
            execution_type = order.get("x")
            
            logger.info(f"📋 订单更新: {symbol} ID={order_id} 状态={order_status} 执行类型={execution_type}")
            
            # 调用回调
            if self.order_update_callback:
                await self.order_update_callback({
                    "symbol": symbol,
                    "order_id": order_id,
                    "order_status": order_status,
                    "execution_type": execution_type,
                    "side": order.get("S"),
                    "order_type": order.get("o"),
                    "quantity": float(order.get("q", 0)),
                    "price": float(order.get("p", 0)),
                    "timestamp": data.get("E")
                })
                
        except Exception as e:
            logger.error(f"❌ 处理订单更新失败: {e}")


# 全局WebSocket实例缓存
_websocket_clients: Dict[str, BinanceWebSocket] = {}


async def get_binance_websocket(testnet: bool = False) -> BinanceWebSocket:
    """
    获取币安WebSocket客户端（单例）
    
    Args:
        testnet: 是否测试网
    
    Returns:
        WebSocket客户端实例
    """
    key = "testnet" if testnet else "mainnet"
    
    if key not in _websocket_clients:
        client = BinanceWebSocket(testnet)
        await client.connect()
        _websocket_clients[key] = client
    
    return _websocket_clients[key]


async def close_all_websockets():
    """关闭所有WebSocket连接"""
    for client in _websocket_clients.values():
        await client.disconnect()
    _websocket_clients.clear()
