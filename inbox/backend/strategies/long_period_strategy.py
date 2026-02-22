"""
长周期策略示例 - 支持需要大量历史数据的策略（如SMA777）

这个策略演示了如何：
1. 声明需要的历史K线数量
2. 在启动时预加载历史数据
3. 实现"交接棒"逻辑，正确处理历史数据和实时数据的衔接
"""
from core.strategy_base import BaseStrategy, Signal
from typing import Optional, Dict, Any
from core.binance_client import BinanceClient
from loguru import logger


class LongPeriodStrategy(BaseStrategy):
    """
    长周期均线策略
    
    策略逻辑：
    - 计算SMA777（777周期简单移动平均线）
    - 当价格上穿SMA777时，设置TRIGGER
    - 在Tick中检查TRIGGER并生成买入信号
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # ⚠️ 重要：所有参数必须从config中读取，禁止写死
        # 如果策略需要自定义参数，应该在config中传入
        self.longest_period = config.get("longest_period", 777)  # 默认777，但可以从配置覆盖
        
        # 初始化策略状态
        self.state.update({
            "prices": [],  # 存储历史收盘价
            "sma777": None,  # SMA777指标值
            "trigger": False  # 交易触发器
        })
        
        logger.info(f"✅ 长周期策略初始化完成，最长周期={self.longest_period}")
    
    def get_required_history_length(self) -> int:
        """
        告诉系统我们需要多少根历史K线
        
        ⚠️ 重要：这个值应该根据策略的longest_period动态计算，禁止写死
        """
        return self.longest_period
    
    async def prepare_data(self, client: BinanceClient):
        """
        在启动时加载历史K线数据
        
        这个方法会在策略启动时被调用一次，用于预加载历史数据
        """
        # ⚠️ 重要：symbol和timeframe必须从self.config中读取，禁止写死
        symbol = self.config.get("symbols", ["BTC/USDT"])[0]  # 取第一个交易对
        timeframe = self.timeframe  # 从基类继承的timeframe
        
        logger.info(f"📊 开始为 {symbol} 加载 {self.longest_period} 根 {timeframe} 历史K线...")
        
        # 调用客户端获取历史K线
        historical_klines = await client.fetch_historical_klines(
            symbol=symbol,
            timeframe=timeframe,
            limit=self.longest_period
        )
        
        # 检查是否获取到足够的数据
        if historical_klines and len(historical_klines) >= self.longest_period:
            # 提取收盘价并存储
            self.state["prices"] = [k["close"] for k in historical_klines]
            
            # 记录最后一根K线的时间戳（用于"交接棒"逻辑）
            self.state['last_kline_timestamp'] = historical_klines[-1]["timestamp"]
            
            # 计算初始指标
            self.calculate_indicators()
            
            logger.info(f"✅ 历史数据加载完成，初始SMA{self.longest_period}: {self.state['sma777']:.2f}")
        else:
            logger.warning(f"⚠️ 历史数据不足，获取到 {len(historical_klines) if historical_klines else 0} 根，需要 {self.longest_period} 根")
    
    def calculate_indicators(self):
        """
        计算所有技术指标
        
        ⚠️ 重要：确保有足够的数据再计算
        """
        if len(self.state["prices"]) >= self.longest_period:
            # 计算SMA777：取最近777根K线的收盘价平均值
            self.state["sma777"] = sum(self.state["prices"][-self.longest_period:]) / self.longest_period
    
    def on_kline(self, kline: Dict[str, Any]):
        """
        处理K线数据（低频触发）
        
        ⚠️ 重要：实现"交接棒"逻辑，正确处理历史数据和实时数据的衔接
        """
        new_kline_timestamp = kline["timestamp"]
        last_known_timestamp = self.state['last_kline_timestamp']
        
        # 情况1：新K线（时间戳更大）
        if new_kline_timestamp > last_known_timestamp:
            # 添加新K线的收盘价
            self.state["prices"].append(kline["close"])
            # 更新时间戳
            self.state['last_kline_timestamp'] = new_kline_timestamp
            
            # 保持列表长度，只保留最近的N根
            if len(self.state["prices"]) > self.longest_period:
                self.state["prices"] = self.state["prices"][-self.longest_period:]
            
            logger.debug(f"📈 新K线: close={kline['close']}, timestamp={new_kline_timestamp}")
        
        # 情况2：更新当前K线（时间戳相同）
        elif new_kline_timestamp == last_known_timestamp:
            # 更新最后一根K线的收盘价
            self.state["prices"][-1] = kline["close"]
            logger.debug(f"🔄 更新K线: close={kline['close']}, timestamp={new_kline_timestamp}")
        
        # 情况3：旧数据（时间戳更小）
        else:
            # 忽略旧数据
            logger.debug(f"⏪ 忽略旧K线: timestamp={new_kline_timestamp} < {last_known_timestamp}")
            return
        
        # 重新计算指标
        self.calculate_indicators()
        
        # --- 策略逻辑 ---
        if self.state["sma777"] is not None:
            # 检测价格上穿SMA777
            if kline["close"] > self.state["sma777"]:
                if not self.state.get("trigger", False):
                    self.state["trigger"] = True
                    logger.info(f"🔔 价格 {kline['close']:.2f} 上穿 SMA{self.longest_period} {self.state['sma777']:.2f}，设置TRIGGER")
    
    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """
        处理Tick数据（高频触发）
        
        检查TRIGGER状态，如果为True则生成交易信号
        """
        # 检查TRIGGER
        if not self.state.get("trigger", False):
            return None
        
        # 生成买入信号
        signal = Signal(
            action="BUY",
            symbol=tick["symbol"],
            price=tick["price"],
            reason=f"价格上穿SMA{self.longest_period}"
        )
        
        # 清除TRIGGER
        self.state["trigger"] = False
        
        logger.info(f"🎯 生成交易信号: {signal}")
        return signal
