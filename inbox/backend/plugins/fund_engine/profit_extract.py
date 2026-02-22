"""
盈利提取插件 - 完整实现
支持钱包阈值和倍数模式两种提取方式
"""
from typing import Dict, Tuple, Optional
from enum import Enum
from loguru import logger


class ExtractionMode(str, Enum):
    """提取模式"""
    WALLET_THRESHOLD = "wallet_threshold"  # 钱包阈值模式
    MULTIPLE_MODE = "multiple_mode"  # 倍数模式


class ProfitExtractionEngine:
    """
    盈利提取引擎
    
    实现两种提取模式的完整数学公式
    """
    
    def __init__(self, config: Dict):
        """
        初始化盈利提取引擎
        
        Args:
            config: 配置参数
                {
                    "mode": "wallet_threshold" | "multiple_mode",
                    "initial_margin": 1000,  # 初始保证金 Y
                    "threshold": 2000,  # 提取阈值 X (钱包阈值模式)
                    "multiple": 2.0,  # 倍数阈值 X (倍数模式)
                    "max_extract_ratio": 0.2  # 最大提取比例 r_max (可选)
                }
        """
        self.mode = ExtractionMode(config.get("mode", "wallet_threshold"))
        self.initial_margin = config.get("initial_margin", 1000)  # Y
        self.threshold = config.get("threshold", 2000)  # X (钱包阈值模式)
        self.multiple = config.get("multiple", 2.0)  # X (倍数模式)
        self.max_extract_ratio = config.get("max_extract_ratio", None)  # r_max
        
        logger.info(f"✅ 盈利提取引擎初始化: 模式={self.mode.value}, 初始保证金={self.initial_margin}")
    
    def check_and_calculate(self, current_balance: float) -> Tuple[bool, float]:
        """
        检查是否触发提取并计算提取金额（核心方法）
        
        Args:
            current_balance: 当前余额（钱包余额W 或 保证金余额B）
        
        Returns:
            (是否触发, 提取金额)
        """
        if self.mode == ExtractionMode.WALLET_THRESHOLD:
            return self._check_wallet_threshold(current_balance)
        else:
            return self._check_multiple_mode(current_balance)
    
    def _check_wallet_threshold(self, wallet_balance: float) -> Tuple[bool, float]:
        """
        钱包阈值模式
        
        公式：
        1. 触发条件: W >= X (且 X > Y)
        2. 划转金额: T = W - Y
        3. 提取后钱包余额: W' = Y
        
        Args:
            wallet_balance: 钱包余额 W
        
        Returns:
            (是否触发, 提取金额)
        """
        W = wallet_balance
        X = self.threshold
        Y = self.initial_margin
        
        # 验证阈值设置
        if X <= Y:
            logger.warning(f"⚠️ 阈值设置错误: X={X} 必须大于 Y={Y}")
            return False, 0
        
        # 检查触发条件
        if W < X:
            logger.debug(f"未触发提取: W={W:.2f} < X={X:.2f}")
            return False, 0
        
        # 计算划转金额: T = W - Y
        T = W - Y
        
        # 应用最大提取比例限制（如果配置了）
        if self.max_extract_ratio:
            T_max = W * self.max_extract_ratio
            T = min(T, T_max)
            logger.debug(f"应用最大提取比例: {self.max_extract_ratio:.2%}, T_max={T_max:.2f}")
        
        logger.info(f"💰 触发钱包阈值提取: W={W:.2f}, T={T:.2f}, W'={W-T:.2f}")
        return True, T
    
    def _check_multiple_mode(self, margin_balance: float) -> Tuple[bool, float]:
        """
        倍数模式
        
        公式：
        1. 阈值计算: T_threshold = X * Y
        2. 触发条件: B >= T_threshold (且 X > 1)
        3. 划转金额: T = B - Y
        4. 提取后保证金余额: B' = Y
        
        Args:
            margin_balance: 保证金余额 B
        
        Returns:
            (是否触发, 提取金额)
        """
        B = margin_balance
        X = self.multiple
        Y = self.initial_margin
        
        # 验证倍数设置
        if X <= 1:
            logger.warning(f"⚠️ 倍数设置错误: X={X} 必须大于 1")
            return False, 0
        
        # 计算阈值: T_threshold = X * Y
        T_threshold = X * Y
        
        # 检查触发条件
        if B < T_threshold:
            logger.debug(f"未触发提取: B={B:.2f} < T_threshold={T_threshold:.2f}")
            return False, 0
        
        # 计算划转金额: T = B - Y
        T = B - Y
        
        # 应用最大提取比例限制（如果配置了）
        if self.max_extract_ratio:
            T_max = B * self.max_extract_ratio
            T = min(T, T_max)
            logger.debug(f"应用最大提取比例: {self.max_extract_ratio:.2%}, T_max={T_max:.2f}")
        
        logger.info(f"💰 触发倍数模式提取: B={B:.2f}, 阈值={T_threshold:.2f}, T={T:.2f}, B'={B-T:.2f}")
        return True, T
    
    def get_next_threshold(self) -> float:
        """
        获取下一次提取的阈值
        
        Returns:
            阈值金额
        """
        if self.mode == ExtractionMode.WALLET_THRESHOLD:
            return self.threshold
        else:
            return self.multiple * self.initial_margin
    
    def get_status(self) -> Dict:
        """
        获取提取引擎状态
        
        Returns:
            状态信息字典
        """
        return {
            "mode": self.mode.value,
            "initial_margin": self.initial_margin,
            "threshold": self.threshold if self.mode == ExtractionMode.WALLET_THRESHOLD else None,
            "multiple": self.multiple if self.mode == ExtractionMode.MULTIPLE_MODE else None,
            "next_threshold": self.get_next_threshold(),
            "max_extract_ratio": self.max_extract_ratio
        }


class InitialCapitalProtection:
    """
    初始金额保护
    
    公式：
    1. 保护阈值: Threshold_protect = Y * X_protect
    2. 触发条件: (复利启用) AND (k_protect < N_protect) AND (B_total >= Threshold_protect)
    3. 划转金额: T_protect = truncate(Y * (X_protect - 1), step_transfer)
    """
    
    def __init__(self, config: Dict):
        """
        初始化初始金额保护
        
        Args:
            config: 配置参数
                {
                    "initial_amount": 1000,  # 初始金额 Y
                    "protect_multiple": 2.0,  # 保护倍数 X_protect
                    "max_protect_count": 1,  # 最大保护次数 N_protect
                    "transfer_step": 10  # 划转步长 step_transfer
                }
        """
        self.initial_amount = config.get("initial_amount", 1000)  # Y
        self.protect_multiple = config.get("protect_multiple", 2.0)  # X_protect
        self.max_protect_count = config.get("max_protect_count", 1)  # N_protect
        self.transfer_step = config.get("transfer_step", 10)  # step_transfer
        
        # 当前已执行保护次数
        self.protect_count = 0  # k_protect
        
        # 计算保护阈值
        self.threshold = self.initial_amount * self.protect_multiple
        
        logger.info(f"✅ 初始金额保护初始化: 阈值={self.threshold:.2f}, 最大次数={self.max_protect_count}")
    
    def check_and_calculate(self, total_balance: float, compounding_enabled: bool) -> Tuple[bool, float]:
        """
        检查是否触发保护并计算划转金额
        
        Args:
            total_balance: 总余额 B_total
            compounding_enabled: 复利是否启用
        
        Returns:
            (是否触发, 划转金额)
        """
        # 触发条件检查
        if not compounding_enabled:
            logger.debug("复利未启用，不触发保护")
            return False, 0
        
        if self.protect_count >= self.max_protect_count:
            logger.debug(f"已达最大保护次数: {self.protect_count}/{self.max_protect_count}")
            return False, 0
        
        if total_balance < self.threshold:
            logger.debug(f"未达保护阈值: {total_balance:.2f} < {self.threshold:.2f}")
            return False, 0
        
        # 计算划转金额: T_protect = truncate(Y * (X_protect - 1), step_transfer)
        T_protect = self.initial_amount * (self.protect_multiple - 1)
        T_protect = self._truncate(T_protect, self.transfer_step)
        
        # 增加保护次数
        self.protect_count += 1
        
        logger.info(f"🛡️ 触发初始金额保护: 次数={self.protect_count}/{self.max_protect_count}, T={T_protect:.2f}")
        return True, T_protect
    
    def _truncate(self, amount: float, step: float) -> float:
        """
        按步长截断金额
        
        Args:
            amount: 原始金额
            step: 步长
        
        Returns:
            截断后的金额
        """
        return (amount // step) * step


class ProfitMultipleEndpoint:
    """
    盈利倍数终点
    
    公式：
    1. 终点阈值: Threshold_end = Y * X_end
    2. 触发条件: B_total >= Threshold_end
    3. 划转金额: T_end = truncate(Y * (X_end - 1), step_transfer)
    """
    
    def __init__(self, config: Dict):
        """
        初始化盈利倍数终点
        
        Args:
            config: 配置参数
                {
                    "initial_amount": 1000,  # 初始金额 Y
                    "endpoint_multiple": 10.0,  # 终点倍数 X_end
                    "transfer_step": 10  # 划转步长 step_transfer
                }
        """
        self.initial_amount = config.get("initial_amount", 1000)  # Y
        self.endpoint_multiple = config.get("endpoint_multiple", 10.0)  # X_end
        self.transfer_step = config.get("transfer_step", 10)  # step_transfer
        
        # 计算终点阈值
        self.threshold = self.initial_amount * self.endpoint_multiple
        
        # 是否已触发
        self.triggered = False
        
        logger.info(f"✅ 盈利倍数终点初始化: 阈值={self.threshold:.2f}")
    
    def check_and_calculate(self, total_balance: float) -> Tuple[bool, float]:
        """
        检查是否触发终点并计算划转金额
        
        Args:
            total_balance: 总余额 B_total
        
        Returns:
            (是否触发, 划转金额)
        """
        # 如果已触发过，不再触发
        if self.triggered:
            return False, 0
        
        # 检查触发条件
        if total_balance < self.threshold:
            logger.debug(f"未达终点阈值: {total_balance:.2f} < {self.threshold:.2f}")
            return False, 0
        
        # 计算划转金额: T_end = truncate(Y * (X_end - 1), step_transfer)
        T_end = self.initial_amount * (self.endpoint_multiple - 1)
        T_end = self._truncate(T_end, self.transfer_step)
        
        # 标记为已触发
        self.triggered = True
        
        logger.info(f"🎯 触发盈利倍数终点: B_total={total_balance:.2f}, T={T_end:.2f}")
        return True, T_end
    
    def _truncate(self, amount: float, step: float) -> float:
        """按步长截断金额"""
        return (amount // step) * step


# 示例使用
if __name__ == "__main__":
    print("\n=== 盈利提取测试 ===")
    
    # 测试钱包阈值模式
    config1 = {
        "mode": "wallet_threshold",
        "initial_margin": 1000,
        "threshold": 2000,
        "max_extract_ratio": 0.2
    }
    
    engine1 = ProfitExtractionEngine(config1)
    
    test_balances = [1500, 2000, 2500, 3000]
    for balance in test_balances:
        triggered, amount = engine1.check_and_calculate(balance)
        print(f"钱包余额={balance:.2f} -> 触发={triggered}, 提取金额={amount:.2f}")
    
    # 测试倍数模式
    print("\n=== 倍数模式测试 ===")
    config2 = {
        "mode": "multiple_mode",
        "initial_margin": 1000,
        "multiple": 2.0
    }
    
    engine2 = ProfitExtractionEngine(config2)
    
    for balance in test_balances:
        triggered, amount = engine2.check_and_calculate(balance)
        print(f"保证金余额={balance:.2f} -> 触发={triggered}, 提取金额={amount:.2f}")
