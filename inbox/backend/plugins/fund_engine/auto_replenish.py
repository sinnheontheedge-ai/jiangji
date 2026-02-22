"""
自动补足余额引擎

功能：当合约账户总余额低于初始资金时，自动从现货账户转入USDT
作者：THE KA INC.
版本：v1.0
"""
from typing import Dict, Tuple, Optional
from loguru import logger


class AutoReplenishEngine:
    """
    自动补足余额引擎
    
    核心功能：
    - 监控合约账户的总余额（Total Balance）
    - 当总余额低于初始资金时，自动从现货账户转入USDT
    - 保持合约账户总余额不低于初始资金
    
    数学公式：
    1. 触发条件: B_total < Y_initial
    2. 补足金额: T_replenish = Y_initial - B_total
    3. 前提条件: B_spot >= T_replenish
    4. 补足后余额: B_total' = Y_initial
    
    其中：
    - B_total = 合约账户总余额（Total Balance）
    - Y_initial = 初始资金
    - B_spot = 现货账户余额
    - T_replenish = 需要补足的金额
    """
    
    def __init__(self, config: Dict):
        """
        初始化自动补足余额引擎
        
        Args:
            config: 配置参数
                {
                    "initial_capital": 1000,  # 初始资金 Y_initial (USDT)
                    "check_interval": 60,  # 检查间隔（秒）
                    "min_transfer_amount": 10,  # 最小转账金额（USDT）
                    "enable_alert": True,  # 启用余额不足告警
                    "alert_threshold": 0.8,  # 告警阈值（初始资金的百分比）
                    "max_replenish_per_day": 10  # 每日最大补足次数
                }
        
        Example:
            >>> config = {
            ...     "initial_capital": 1000,
            ...     "check_interval": 60,
            ...     "min_transfer_amount": 10,
            ...     "enable_alert": True
            ... }
            >>> engine = AutoReplenishEngine(config)
        """
        self.initial_capital = config.get("initial_capital", 1000)  # Y_initial
        self.check_interval = config.get("check_interval", 60)
        self.min_transfer_amount = config.get("min_transfer_amount", 10)
        self.enable_alert = config.get("enable_alert", True)
        self.alert_threshold = config.get("alert_threshold", 0.8)
        self.max_replenish_per_day = config.get("max_replenish_per_day", 10)
        
        # 统计信息
        self.replenish_count_today = 0  # 今日补足次数
        self.total_replenished = 0.0  # 累计补足金额
        
        logger.info(
            f"✅ 自动补足余额引擎初始化: "
            f"初始资金={self.initial_capital:.2f} USDT, "
            f"检查间隔={self.check_interval}秒"
        )
    
    def check_and_calculate(
        self, 
        contract_total_balance: float, 
        spot_balance: float
    ) -> Tuple[bool, float, str]:
        """
        检查是否需要补足并计算转账金额（核心方法）
        
        公式：
        1. 触发条件: B_total < Y_initial
        2. 补足金额: T_replenish = Y_initial - B_total
        3. 安全检查: B_spot >= T_replenish
        
        Args:
            contract_total_balance: 合约账户总余额 B_total
            spot_balance: 现货账户余额 B_spot
        
        Returns:
            (是否需要补足, 转账金额, 告警信息)
            
        Example:
            >>> engine = AutoReplenishEngine({"initial_capital": 1000})
            >>> # 合约总余额800，现货余额500
            >>> need, amount, msg = engine.check_and_calculate(800, 500)
            >>> print(f"需要补足: {need}, 金额: {amount}")
            需要补足: True, 金额: 200.0
        """
        B_total = contract_total_balance
        Y_initial = self.initial_capital
        B_spot = spot_balance
        
        # 检查触发条件: B_total < Y_initial
        if B_total >= Y_initial:
            logger.debug(
                f"合约总余额充足: B_total={B_total:.2f} >= Y_initial={Y_initial:.2f}"
            )
            return False, 0, ""
        
        # 计算补足金额: T_replenish = Y_initial - B_total
        T_replenish = Y_initial - B_total
        
        logger.info(
            f"📊 检测到余额不足: "
            f"合约总余额={B_total:.2f}, "
            f"初始资金={Y_initial:.2f}, "
            f"需补足={T_replenish:.2f}"
        )
        
        # 检查是否低于最小转账金额
        if T_replenish < self.min_transfer_amount:
            logger.debug(
                f"补足金额 {T_replenish:.2f} 低于最小转账金额 {self.min_transfer_amount:.2f}"
            )
            return False, 0, ""
        
        # 检查每日补足次数限制
        if self.replenish_count_today >= self.max_replenish_per_day:
            alert_msg = (
                f"⚠️ 已达每日最大补足次数限制！"
                f"今日已补足 {self.replenish_count_today} 次"
            )
            logger.warning(alert_msg)
            return False, 0, alert_msg
        
        # 安全检查: 现货账户余额是否充足
        if B_spot < T_replenish:
            alert_msg = (
                f"🚨 现货账户余额不足！"
                f"需要: {T_replenish:.2f} USDT, "
                f"可用: {B_spot:.2f} USDT, "
                f"缺口: {T_replenish - B_spot:.2f} USDT"
            )
            logger.error(alert_msg)
            
            # 如果现货账户有余额，尝试转入全部
            if B_spot >= self.min_transfer_amount:
                logger.warning(
                    f"⚠️ 将转入现货账户全部余额: {B_spot:.2f} USDT "
                    f"(无法完全补足到初始资金)"
                )
                return True, B_spot, alert_msg
            else:
                return False, 0, alert_msg
        
        # 告警阈值检查
        if self.enable_alert:
            alert_ratio = B_total / Y_initial
            if alert_ratio < self.alert_threshold:
                logger.warning(
                    f"⚠️ 合约账户余额过低！"
                    f"当前余额比例: {alert_ratio:.1%} "
                    f"(低于告警阈值 {self.alert_threshold:.1%})"
                )
        
        logger.info(
            f"🔄 准备执行自动补足: "
            f"转账金额={T_replenish:.2f} USDT, "
            f"补足后余额={B_total + T_replenish:.2f} USDT"
        )
        
        return True, T_replenish, ""
    
    def execute_replenish(
        self, 
        amount: float, 
        account_id: int,
        exchange_client
    ) -> bool:
        """
        执行补足操作（从现货账户转入合约账户）
        
        Args:
            amount: 转账金额
            account_id: 账户ID
            exchange_client: 交易所客户端
        
        Returns:
            是否成功
        """
        try:
            logger.info(
                f"🔄 开始执行补足: "
                f"账户ID={account_id}, "
                f"金额={amount:.2f} USDT"
            )
            
            # 调用交易所API：从现货账户转入合约账户
            # transfer_type: SPOT -> FUTURES
            result = exchange_client.transfer_between_accounts(
                asset='USDT',
                amount=amount,
                from_account='SPOT',  # 现货账户
                to_account='FUTURES'  # 合约账户
            )
            
            if result.get('success'):
                # 更新统计信息
                self.replenish_count_today += 1
                self.total_replenished += amount
                
                logger.info(
                    f"✅ 补足成功！"
                    f"金额={amount:.2f} USDT, "
                    f"今日第 {self.replenish_count_today} 次补足, "
                    f"累计补足={self.total_replenished:.2f} USDT"
                )
                return True
            else:
                error_msg = result.get('error', '未知错误')
                logger.error(f"❌ 补足失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 补足异常: {str(e)}")
            return False
    
    def get_status(self) -> Dict:
        """
        获取引擎状态
        
        Returns:
            状态信息字典
        """
        return {
            "initial_capital": self.initial_capital,
            "check_interval": self.check_interval,
            "min_transfer_amount": self.min_transfer_amount,
            "replenish_count_today": self.replenish_count_today,
            "total_replenished": self.total_replenished,
            "max_replenish_per_day": self.max_replenish_per_day,
            "alert_threshold": self.alert_threshold
        }
    
    def reset_daily_counter(self):
        """
        重置每日计数器（由定时任务在每天0点调用）
        """
        logger.info(
            f"🔄 重置每日计数器: "
            f"昨日补足次数={self.replenish_count_today}"
        )
        self.replenish_count_today = 0


# 使用示例
if __name__ == "__main__":
    # 配置
    config = {
        "initial_capital": 1000,
        "check_interval": 60,
        "min_transfer_amount": 10,
        "enable_alert": True,
        "alert_threshold": 0.8,
        "max_replenish_per_day": 10
    }
    
    # 创建引擎
    engine = AutoReplenishEngine(config)
    
    # 场景1: 合约余额充足
    print("\n场景1: 合约余额充足")
    need, amount, msg = engine.check_and_calculate(1200, 500)
    print(f"需要补足: {need}, 金额: {amount}, 信息: {msg}")
    
    # 场景2: 合约余额不足，现货充足
    print("\n场景2: 合约余额不足，现货充足")
    need, amount, msg = engine.check_and_calculate(800, 500)
    print(f"需要补足: {need}, 金额: {amount}, 信息: {msg}")
    
    # 场景3: 合约余额不足，现货也不足
    print("\n场景3: 合约余额不足，现货也不足")
    need, amount, msg = engine.check_and_calculate(800, 50)
    print(f"需要补足: {need}, 金额: {amount}, 信息: {msg}")
    
    # 场景4: 补足金额过小
    print("\n场景4: 补足金额过小")
    need, amount, msg = engine.check_and_calculate(995, 500)
    print(f"需要补足: {need}, 金额: {amount}, 信息: {msg}")
