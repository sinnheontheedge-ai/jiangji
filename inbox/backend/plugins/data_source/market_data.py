"""
行情数据源插件 - 完整实现
支持WebSocket实时订阅K线和Tick数据
"""
import asyncio
import json
from typing import Dict, List, Set, Callable, Optional
from datetime import datetime
from loguru import logger

from core.event_bus import EventBus


class MarketDataSource:
    """
    行情数据源
    
    职责：
    1. 连接交易所WebSocket
    2. 订阅K线和Tick数据
    3. 发布行情事件到事件总线
    """
    
    def __init__(self, config: Dict):
        """
        初始化行情数据源
        
        Args:
            config: 配置参数
                {
                    "exchange": "binance",
                    "testnet": False,
                    "reconnect_interval": 5
                }
        """
        self.exchange = config.get("exchange", "binance")
        self.testnet = config.get("testnet", False)
        self.reconnect_interval = config.get("reconnect_interval", 5)
        
        # WebSocket连接
        self.ws = None
        self.running = False
        
        # 订阅管理
        self.kline_subscriptions: Set[tuple] = set()  # (symbol, timeframe)
        self.tick_subscriptions: Set[str] = set()  # symbol
        
        # 事件总线
        self.event_bus = EventBus.get_instance()
        
        logger.info(f"✅ 行情数据源初始化: 交易所={self.exchange}, 测试网={self.testnet}")
    
    async def start(self):
        """启动数据源"""
        self.running = True
        
        # 连接币安WebSocket
        from core.binance_websocket import get_binance_websocket
        self.ws = await get_binance_websocket(self.testnet)
        
        # 设置回调函数
        self.ws.set_kline_callback(self._handle_kline)
        self.ws.set_tick_callback(self._handle_tick)
        
        logger.info("✅ 行情数据源已启动（真实WebSocket连接）")
    
    async def stop(self):
        """停止数据源"""
        self.running = False
        
        if self.ws:
            await self.ws.disconnect()
        
        logger.info("👋 行情数据源已停止")
    
    async def subscribe_kline(self, symbol: str, timeframe: str):
        """
        订阅K线数据
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            timeframe: 时间周期，如 "15m"
        """
        subscription = (symbol, timeframe)
        
        if subscription in self.kline_subscriptions:
            logger.debug(f"已订阅K线: {symbol} {timeframe}")
            return
        
        self.kline_subscriptions.add(subscription)
        
        # 发送订阅请求到币安WebSocket
        if self.ws:
            await self.ws.subscribe_kline(symbol, timeframe)
        
        logger.info(f"📊 订阅K线: {symbol} {timeframe}")
    
    async def subscribe_tick(self, symbol: str):
        """
        订阅Tick数据
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
        """
        if symbol in self.tick_subscriptions:
            logger.debug(f"已订阅Tick: {symbol}")
            return
        
        self.tick_subscriptions.add(symbol)
        
        # 发送订阅请求到币安WebSocket
        if self.ws:
            await self.ws.subscribe_ticker(symbol)
        
        logger.info(f"📈 订阅Tick: {symbol}")
    
    async def unsubscribe_kline(self, symbol: str, timeframe: str):
        """取消订阅K线"""
        subscription = (symbol, timeframe)
        
        if subscription in self.kline_subscriptions:
            self.kline_subscriptions.remove(subscription)
            logger.info(f"🔕 取消订阅K线: {symbol} {timeframe}")
    
    async def unsubscribe_tick(self, symbol: str):
        """取消订阅Tick"""
        if symbol in self.tick_subscriptions:
            self.tick_subscriptions.remove(symbol)
            logger.info(f"🔕 取消订阅Tick: {symbol}")
    
    async def _handle_kline(self, kline_data: Dict):
        """
        处理K线数据回调
        
        Args:
            kline_data: K线数据
                {
                    'symbol': 'BTCUSDT',
                    'interval': '1m',
                    'timestamp': 1638747600000,
                    'open': 50000.0,
                    'high': 50200.0,
                    'low': 49900.0,
                    'close': 50100.0,
                    'volume': 100.5,
                    'is_closed': False
                }
        """
        try:
            symbol = kline_data['symbol']
            interval = kline_data['interval']
            
            # 转换为系统格式
            formatted_data = {
                "symbol": symbol,
                "timeframe": interval,
                "open": kline_data['open'],
                "high": kline_data['high'],
                "low": kline_data['low'],
                "close": kline_data['close'],
                "volume": kline_data['volume'],
                "timestamp": kline_data['timestamp'] // 1000,  # 转换为秒
                "is_closed": kline_data['is_closed']
            }
            
            # 发布K线事件到事件总线
            channel = f"market_data:kline:{symbol}:{interval}"
            await self.event_bus.publish(channel, formatted_data)
            
            if kline_data['is_closed']:
                logger.debug(f"📊 K线完成: {symbol} {interval} close={kline_data['close']}")
            
        except Exception as e:
            logger.error(f"❌ 处理K线数据失败: {e}")
    
    async def _handle_tick(self, tick_data: Dict):
        """
        处理Tick数据回调
        
        Args:
            tick_data: Tick数据
                {
                    'symbol': 'BTCUSDT',
                    'price': 50000.0,
                    'volume': 10000.5,
                    'timestamp': 1638747660000
                }
        """
        try:
            symbol = tick_data['symbol']
            
            # 转换为系统格式
            formatted_data = {
                "symbol": symbol,
                "price": tick_data['price'],
                "volume": tick_data.get('volume', 0),
                "timestamp": tick_data['timestamp'] // 1000  # 转换为秒
            }
            
            # 发布Tick事件到事件总线
            channel = f"market_data:tick:{symbol}"
            await self.event_bus.publish(channel, formatted_data)
            
            # 发布价格更新事件
            await self.event_bus.publish("price:update", {
                "symbol": symbol,
                "price": tick_data['price'],
                "timestamp": formatted_data['timestamp']
            })
            
            logger.debug(f"📈 Tick更新: {symbol} price={tick_data['price']}")
            
        except Exception as e:
            logger.error(f"❌ 处理Tick数据失败: {e}")
    
    def get_subscriptions(self) -> Dict:
        """
        获取当前订阅状态
        
        Returns:
            订阅信息字典
        """
        return {
            "kline_subscriptions": list(self.kline_subscriptions),
            "tick_subscriptions": list(self.tick_subscriptions),
            "total_subscriptions": len(self.kline_subscriptions) + len(self.tick_subscriptions)
        }


class BinanceWebSocketClient:
    """
    币安WebSocket客户端（真实实现示例）
    
    实际项目中使用此类替换模拟数据生成器
    """
    
    def __init__(self, testnet: bool = False):
        """
        初始化币安WebSocket客户端
        
        Args:
            testnet: 是否使用测试网
        """
        self.testnet = testnet
        
        if testnet:
            self.ws_url = "wss://testnet.binance.vision/ws"
        else:
            self.ws_url = "wss://stream.binance.com:9443/ws"
        
        self.ws = None
        self.running = False
        
        logger.info(f"✅ 币安WebSocket客户端初始化: URL={self.ws_url}")
    
    async def connect(self):
        """
        连接WebSocket
        
        实际实现时需要：
        1. 使用websockets库: import websockets
        2. self.ws = await websockets.connect(self.ws_url)
        3. 启动消息接收循环
        """
        logger.info("🔌 连接币安WebSocket...")
        
        # 实际代码示例（需要安装websockets库）:
        # import websockets
        # self.ws = await websockets.connect(self.ws_url)
        # self.running = True
        # asyncio.create_task(self._receive_messages())
        
        pass
    
    async def subscribe_kline(self, symbol: str, interval: str):
        """
        订阅K线
        
        Args:
            symbol: 交易对，如 "btcusdt"
            interval: 时间周期，如 "15m"
        """
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@kline_{interval}"],
            "id": 1
        }
        
        # 发送订阅消息
        # await self.ws.send(json.dumps(subscribe_message))
        
        logger.info(f"📊 订阅币安K线: {symbol} {interval}")
    
    async def subscribe_ticker(self, symbol: str):
        """
        订阅Ticker（Tick数据）
        
        Args:
            symbol: 交易对，如 "btcusdt"
        """
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@ticker"],
            "id": 2
        }
        
        # 发送订阅消息
        # await self.ws.send(json.dumps(subscribe_message))
        
        logger.info(f"📈 订阅币安Ticker: {symbol}")
    
    async def _receive_messages(self):
        """
        接收WebSocket消息
        
        实际实现时需要：
        1. 循环接收消息
        2. 解析JSON数据
        3. 根据数据类型分发到不同的处理器
        """
        while self.running:
            try:
                # message = await self.ws.recv()
                # data = json.loads(message)
                # 
                # if 'e' in data:
                #     if data['e'] == 'kline':
                #         await self._handle_kline(data)
                #     elif data['e'] == '24hrTicker':
                #         await self._handle_ticker(data)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ 接收消息异常: {e}")
                break
    
    async def close(self):
        """关闭WebSocket连接"""
        self.running = False
        
        if self.ws:
            # await self.ws.close()
            pass
        
        logger.info("👋 币安WebSocket已关闭")


# 全局行情数据源实例
market_data_source: Optional[MarketDataSource] = None


def get_market_data_source() -> MarketDataSource:
    """获取全局行情数据源实例"""
    global market_data_source
    
    if market_data_source is None:
        config = {
            "exchange": "binance",
            "testnet": True,  # 默认使用测试网
            "reconnect_interval": 5
        }
        market_data_source = MarketDataSource(config)
    
    return market_data_source


# 示例使用
if __name__ == "__main__":
    async def test_market_data():
        """测试行情数据源"""
        # 创建数据源
        config = {
            "exchange": "binance",
            "testnet": True
        }
        source = MarketDataSource(config)
        
        # 启动数据源
        await source.start()
        
        # 订阅数据
        await source.subscribe_kline("BTCUSDT", "15m")
        await source.subscribe_tick("BTCUSDT")
        
        # 运行10秒
        await asyncio.sleep(10)
        
        # 停止数据源
        await source.stop()
    
    # 运行测试
    asyncio.run(test_market_data())
