"""
策略基类 - 所有策略必须继承此类（5个耦合点之一：策略基类接口）
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    """交易信号"""
    action: str  # "BUY" 或 "SELL"
    symbol: str
    quantity: Optional[float] = None
    price: Optional[float] = None
    reason: str = ""


class BaseStrategy(ABC):
    """
    策略基类
    
    所有策略必须实现两个核心方法：
    1. on_kline: 处理K线数据（低频），计算指标、检测事件、设置TRIGGER
    2. on_tick: 处理Tick数据（高频），检查TRIGGER并生成交易信号
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化策略
        
        Args:
            config: 策略配置参数
        """
        self.config = config
        self.symbol = config.get("symbol", "")
        self.timeframe = config.get("timeframe", "15m")
        
        # 策略状态（用于存储指标、TRIGGER等）
        self.state: Dict[str, Any] = {}
        
        # 为"交接棒"逻辑添加状态
        self.state['last_kline_timestamp'] = 0
        
    @abstractmethod
    def get_required_history_length(self) -> int:
        """
        策略启动需要的最少历史K线数量
        
        Returns:
            需要的历史K线数量，如果不需要历史数据则返回0
        """
        pass
    
    @abstractmethod
    async def prepare_data(self, client: Any):
        """
        在策略启动时，加载并准备历史数据
        
        Args:
            client: 交易所客户端，用于获取历史K线
        """
        pass
    
    @abstractmethod
    def on_kline(self, kline: Dict[str, Any]):
        """
        处理K线数据（低频触发）
        
        职责：
        - 计算技术指标（均线、MACD等）
        - 检测事件（金叉、死叉、突破等）
        - 设置TRIGGER状态（self.state['trigger'] = True）
        
        ❌ 不在这里进场！
        
        Args:
            kline: K线数据字典
                {
                    "open": 50000.0,
                    "high": 51000.0,
                    "low": 49500.0,
                    "close": 50500.0,
                    "volume": 1234.56,
                    "timestamp": 1234567890
                }
        """
        pass
    
    @abstractmethod
    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """
        处理Tick数据（高频触发）
        
        职责：
        - 检查TRIGGER状态
        - 如果TRIGGER为True，立即生成交易信号
        - 返回Signal对象或None
        
        ✅ 在这里进场！
        
        Args:
            tick: Tick数据字典
                {
                    "symbol": "BTCUSDT",
                    "price": 50123.45,
                    "timestamp": 1234567890
                }
        
        Returns:
            Signal对象或None
        """
        pass
    
    def reset(self):
        """重置策略状态"""
        self.state = {}
