"""
示例策略：均线金叉做多策略
"""
from core.strategy_base import BaseStrategy, Signal
from typing import Optional, Dict, Any


class MACrossLongStrategy(BaseStrategy):
    """
    均线金叉做多策略
    
    逻辑：
    1. on_kline: 计算快线(MA5)和慢线(MA20)，检测金叉，设置TRIGGER
    2. on_tick: 检查TRIGGER，如果为True则立即做多
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 策略参数
        self.fast_period = config.get("fast_period", 5)
        self.slow_period = config.get("slow_period", 20)
        
        # 状态
        self.state = {
            "prices": [],  # 价格历史
            "fast_ma": None,
            "slow_ma": None,
            "trigger": False,  # 进场触发器
            "prev_fast_ma": None,
            "prev_slow_ma": None
        }
    
    def on_kline(self, kline: Dict[str, Any]):
        """
        处理K线数据
        
        职责：
        1. 更新价格历史
        2. 计算均线
        3. 检测金叉
        4. 设置TRIGGER
        """
        close_price = kline["close"]
        
        # 更新价格历史
        self.state["prices"].append(close_price)
        
        # 只保留最近slow_period个价格
        if len(self.state["prices"]) > self.slow_period:
            self.state["prices"] = self.state["prices"][-self.slow_period:]
        
        # 如果数据不足，无法计算
        if len(self.state["prices"]) < self.slow_period:
            return
        
        # 保存上一次的均线值
        self.state["prev_fast_ma"] = self.state["fast_ma"]
        self.state["prev_slow_ma"] = self.state["slow_ma"]
        
        # 计算均线
        self.state["fast_ma"] = sum(self.state["prices"][-self.fast_period:]) / self.fast_period
        self.state["slow_ma"] = sum(self.state["prices"][-self.slow_period:]) / self.slow_period
        
        # 检测金叉
        if self.state["prev_fast_ma"] and self.state["prev_slow_ma"]:
            # 金叉条件：快线从下方穿越慢线
            if (self.state["prev_fast_ma"] <= self.state["prev_slow_ma"] and 
                self.state["fast_ma"] > self.state["slow_ma"]):
                
                # 设置TRIGGER
                self.state["trigger"] = True
                print(f"🔔 检测到金叉！快线={self.state['fast_ma']:.2f}, 慢线={self.state['slow_ma']:.2f}")
    
    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """
        处理Tick数据
        
        职责：
        1. 检查TRIGGER
        2. 如果TRIGGER为True，生成做多信号
        3. 重置TRIGGER
        """
        # 检查TRIGGER
        if not self.state.get("trigger", False):
            return None
        
        # 生成做多信号
        signal = Signal(
            action="BUY",
            symbol=self.symbol,
            price=tick["price"],
            reason=f"MA金叉做多 (MA{self.fast_period} > MA{self.slow_period})"
        )
        
        # 重置TRIGGER
        self.state["trigger"] = False
        
        return signal
