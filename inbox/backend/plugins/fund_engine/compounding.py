"""
复利系统插件 - 完整实现
支持阶段复利和永续复利两种模式
"""
import math
from typing import Dict, Tuple
from enum import Enum
from loguru import logger


class CompoundingMode(str, Enum):
    """复利模式"""
    STAGE = "stage"  # 阶段复利
    PERPETUAL = "perpetual"  # 永续复利


class CompoundingEngine:
    """
    复利引擎
    
    实现两种复利模式的完整数学公式
    """
    
    def __init__(self, config: Dict):
        """
        初始化复利引擎
        
        Args:
            config: 配置参数
                {
                    "mode": "stage" | "perpetual",
                    "compound_ratio": 20,  # 复利比例 X (%)
                    "initial_base": 1000,  # 初始复利起点 Y
                    "position_percent": 10,  # 仓位百分比 p (%)
                    "concurrent_positions": 1  # 并发仓位数量 n
                }
        """
        self.mode = CompoundingMode(config.get("mode", "stage"))
        self.compound_ratio = config.get("compound_ratio", 20)  # X
        self.initial_base = config.get("initial_base", 1000)  # Y
        self.position_percent = config.get("position_percent", 10)  # p
        self.concurrent_positions = config.get("concurrent_positions", 1)  # n
        
        # 计算复利因子 g = 1 + (X / 100)
        self.compound_factor = 1 + (self.compound_ratio / 100)
        
        # 当前复利起点（阶段复利使用）
        self.current_base = self.initial_base
        
        logger.info(f"✅ 复利引擎初始化: 模式={self.mode.value}, 比例={self.compound_ratio}%, 因子={self.compound_factor}")
    
    def calculate_margin(self, available_balance: float, is_single_position: bool = True) -> float:
        """
        计算保证金（核心方法）
        
        Args:
            available_balance: 可用余额 B
            is_single_position: 是否单仓模式
        
        Returns:
            保证金金额
        """
        if self.mode == CompoundingMode.STAGE:
            return self._calculate_stage_margin(available_balance, is_single_position)
        else:
            return self._calculate_perpetual_margin(available_balance, is_single_position)
    
    def _calculate_stage_margin(self, available_balance: float, is_single_position: bool) -> float:
        """
        阶段复利保证金计算
        
        公式：
        1. 触发条件: B >= Y * g
        2. 多档跨越: while B >= Y * g: Y = Y * g
        3. 下次进场基数: S = Y * g
        4. 单仓保证金: M_single = S * p
        5. 并发保证金: M_each = S / n
        
        Args:
            available_balance: 可用余额 B
            is_single_position: 是否单仓模式
        
        Returns:
            保证金金额
        """
        B = available_balance
        Y = self.current_base
        g = self.compound_factor
        p = self.position_percent / 100
        n = self.concurrent_positions
        
        # 检查是否触发复利升档
        while B >= Y * g:
            Y = Y * g
            logger.info(f"📈 复利升档: 新起点 = {Y:.2f}")
        
        # 更新当前复利起点
        self.current_base = Y
        
        # 计算下次进场基数
        S = Y * g
        
        # 计算保证金
        if is_single_position:
            # 单仓保证金: M_single = S * p
            margin = S * p
            logger.debug(f"💰 单仓保证金: S={S:.2f}, p={p:.2%}, M={margin:.2f}")
        else:
            # 并发保证金: M_each = S / n
            margin = S / n
            logger.debug(f"💰 并发保证金: S={S:.2f}, n={n}, M_each={margin:.2f}")
        
        return margin
    
    def _calculate_perpetual_margin(self, available_balance: float, is_single_position: bool) -> float:
        """
        永续复利保证金计算
        
        公式：
        1. 单仓保证金: M_single = B_close * p
        2. 并发保证金: M_each = B_close / n
        
        Args:
            available_balance: 平仓结算后的可用余额 B_close
            is_single_position: 是否单仓模式
        
        Returns:
            保证金金额
        """
        B_close = available_balance
        p = self.position_percent / 100
        n = self.concurrent_positions
        
        # 计算保证金
        if is_single_position:
            # 单仓保证金: M_single = B_close * p
            margin = B_close * p
            logger.debug(f"💰 永续单仓保证金: B={B_close:.2f}, p={p:.2%}, M={margin:.2f}")
        else:
            # 并发保证金: M_each = B_close / n
            margin = B_close / n
            logger.debug(f"💰 永续并发保证金: B={B_close:.2f}, n={n}, M_each={margin:.2f}")
        
        return margin
    
    def calculate_compound_count(self, current_balance: float) -> int:
        """
        计算复利次数
        
        公式: Compounding Count = floor(log(B / Y) / log(g))
        
        Args:
            current_balance: 当前余额 B
        
        Returns:
            复利次数
        """
        B = current_balance
        Y = self.initial_base
        g = self.compound_factor
        
        if B <= Y or g <= 1:
            return 0
        
        count = math.floor(math.log(B / Y) / math.log(g))
        return count
    
    def calculate_compound_value(self, compound_count: int) -> float:
        """
        计算复利终值
        
        公式: B_n = Y * g^n
        
        Args:
            compound_count: 复利次数 n
        
        Returns:
            复利终值
        """
        Y = self.initial_base
        g = self.compound_factor
        n = compound_count
        
        value = Y * (g ** n)
        return value
    
    def get_next_compound_threshold(self) -> float:
        """
        获取下一次复利升档的阈值
        
        Returns:
            阈值金额
        """
        if self.mode == CompoundingMode.STAGE:
            return self.current_base * self.compound_factor
        else:
            # 永续复利没有固定阈值
            return 0
    
    def reset(self):
        """重置复利状态"""
        self.current_base = self.initial_base
        logger.info("🔄 复利引擎已重置")
    
    def get_status(self) -> Dict:
        """
        获取复利状态
        
        Returns:
            状态信息字典
        """
        return {
            "mode": self.mode.value,
            "compound_ratio": self.compound_ratio,
            "compound_factor": self.compound_factor,
            "initial_base": self.initial_base,
            "current_base": self.current_base,
            "next_threshold": self.get_next_compound_threshold(),
            "position_percent": self.position_percent,
            "concurrent_positions": self.concurrent_positions
        }


# 示例使用
if __name__ == "__main__":
    # 测试阶段复利
    config_stage = {
        "mode": "stage",
        "compound_ratio": 20,
        "initial_base": 1000,
        "position_percent": 10,
        "concurrent_positions": 3
    }
    
    engine = CompoundingEngine(config_stage)
    
    # 测试不同余额下的保证金计算
    test_balances = [1000, 1200, 1500, 2000, 3000]
    
    print("\n=== 阶段复利测试 ===")
    for balance in test_balances:
        margin_single = engine.calculate_margin(balance, is_single_position=True)
        margin_concurrent = engine.calculate_margin(balance, is_single_position=False)
        print(f"余额={balance:.2f} -> 单仓保证金={margin_single:.2f}, 并发保证金={margin_concurrent:.2f}")
    
    # 测试永续复利
    config_perpetual = {
        "mode": "perpetual",
        "position_percent": 10,
        "concurrent_positions": 3
    }
    
    engine2 = CompoundingEngine(config_perpetual)
    
    print("\n=== 永续复利测试 ===")
    for balance in test_balances:
        margin_single = engine2.calculate_margin(balance, is_single_position=True)
        margin_concurrent = engine2.calculate_margin(balance, is_single_position=False)
        print(f"余额={balance:.2f} -> 单仓保证金={margin_single:.2f}, 并发保证金={margin_concurrent:.2f}")
