"""
杠杆与保证金管理器 - 完整实现
处理杠杆降级、保证金计算和爆仓监控
"""
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class MarginInfo:
    """保证金信息"""
    actual_leverage: int  # 实际杠杆
    target_margin: float  # 目标保证金
    actual_margin: float  # 实际保证金
    margin_ratio: float  # 保证金维持率 (%)
    is_safe: bool  # 是否安全


class LeverageManager:
    """
    杠杆管理器
    
    实现完整的杠杆和保证金数学公式
    """
    
    def __init__(self, config: Dict):
        """
        初始化杠杆管理器
        
        Args:
            config: 配置参数
                {
                    "group_leverage": 10,  # 用户组设定杠杆
                    "maintenance_margin_ratio": 0.5  # 维持保证金率 (%)
                }
        """
        self.group_leverage = config.get("group_leverage", 10)  # L_group
        self.maintenance_margin_ratio = config.get("maintenance_margin_ratio", 0.5)  # 维持保证金率
        
        logger.info(f"✅ 杠杆管理器初始化: 组杠杆={self.group_leverage}x, 维持保证金率={self.maintenance_margin_ratio}%")
    
    def calculate_actual_leverage(self, symbol_max_leverage: int) -> int:
        """
        计算实际杠杆
        
        公式: L_actual = min(L_group, L_symbol_max)
        
        Args:
            symbol_max_leverage: 交易对最大允许杠杆 L_symbol_max
        
        Returns:
            实际杠杆
        """
        L_group = self.group_leverage
        L_symbol_max = symbol_max_leverage
        
        L_actual = min(L_group, L_symbol_max)
        
        if L_actual < L_group:
            logger.warning(
                f"⚠️ 杠杆降级: 组杠杆={L_group}x > 交易对最大杠杆={L_symbol_max}x, "
                f"实际使用={L_actual}x"
            )
        else:
            logger.debug(f"✅ 实际杠杆: {L_actual}x")
        
        return L_actual
    
    def calculate_target_margin(self, planned_margin: float, actual_leverage: int) -> float:
        """
        计算杠杆降级时的目标保证金
        
        公式: M_target = M_plan * (L_group / L_actual)
        
        Args:
            planned_margin: 计划保证金 M_plan
            actual_leverage: 实际杠杆 L_actual
        
        Returns:
            目标保证金
        """
        M_plan = planned_margin
        L_group = self.group_leverage
        L_actual = actual_leverage
        
        # 如果没有降级，目标保证金等于计划保证金
        if L_actual == L_group:
            return M_plan
        
        # 杠杆降级时，需要增加保证金
        M_target = M_plan * (L_group / L_actual)
        
        logger.info(
            f"📊 杠杆降级保证金调整: "
            f"计划={M_plan:.2f}, "
            f"目标={M_target:.2f} "
            f"(增加{M_target - M_plan:.2f})"
        )
        
        return M_target
    
    def calculate_actual_margin(self, position_value: float, leverage: int) -> float:
        """
        计算实际保证金
        
        公式: M_actual = V_position / L_actual
        
        Args:
            position_value: 仓位价值 V_position
            leverage: 杠杆倍数 L_actual
        
        Returns:
            实际保证金
        """
        V_position = position_value
        L_actual = leverage
        
        M_actual = V_position / L_actual
        
        logger.debug(f"💰 实际保证金: 仓位价值={V_position:.2f}, 杠杆={L_actual}x, 保证金={M_actual:.2f}")
        
        return M_actual
    
    def calculate_margin_ratio(self, equity: float, used_margin: float) -> float:
        """
        计算保证金维持率
        
        公式: Margin Ratio = (Equity / Used Margin) * 100%
        
        Args:
            equity: 账户权益 Equity
            used_margin: 已用保证金 Used Margin
        
        Returns:
            保证金维持率 (%)
        """
        if used_margin == 0:
            return float('inf')  # 无持仓时维持率为无穷大
        
        margin_ratio = (equity / used_margin) * 100
        
        logger.debug(f"📊 保证金维持率: 权益={equity:.2f}, 已用保证金={used_margin:.2f}, 维持率={margin_ratio:.2f}%")
        
        return margin_ratio
    
    def check_liquidation_risk(self, equity: float, used_margin: float) -> Tuple[bool, float]:
        """
        检查爆仓风险
        
        公式: Margin Ratio < Maintenance Margin Ratio
        
        Args:
            equity: 账户权益
            used_margin: 已用保证金
        
        Returns:
            (是否有爆仓风险, 当前维持率)
        """
        margin_ratio = self.calculate_margin_ratio(equity, used_margin)
        
        is_at_risk = margin_ratio < self.maintenance_margin_ratio
        
        if is_at_risk:
            logger.error(
                f"🚨 爆仓风险警告: "
                f"维持率={margin_ratio:.2f}% < 维持保证金率={self.maintenance_margin_ratio}%"
            )
        
        return is_at_risk, margin_ratio
    
    def calculate_position_size(
        self,
        available_balance: float,
        entry_price: float,
        leverage: int,
        margin_percent: float = 100.0
    ) -> Tuple[float, float]:
        """
        计算仓位大小和所需保证金
        
        Args:
            available_balance: 可用余额
            entry_price: 进场价格
            leverage: 杠杆倍数
            margin_percent: 使用保证金的百分比 (默认100%)
        
        Returns:
            (仓位数量, 所需保证金)
        """
        # 计算可用保证金
        available_margin = available_balance * (margin_percent / 100)
        
        # 计算仓位价值: V = M * L
        position_value = available_margin * leverage
        
        # 计算仓位数量: Q = V / P
        position_quantity = position_value / entry_price
        
        logger.info(
            f"📊 仓位计算: "
            f"可用余额={available_balance:.2f}, "
            f"保证金={available_margin:.2f}, "
            f"杠杆={leverage}x, "
            f"仓位价值={position_value:.2f}, "
            f"数量={position_quantity:.6f}"
        )
        
        return position_quantity, available_margin
    
    def get_margin_info(
        self,
        planned_margin: float,
        position_value: float,
        symbol_max_leverage: int,
        equity: float,
        used_margin: float
    ) -> MarginInfo:
        """
        获取完整的保证金信息
        
        Args:
            planned_margin: 计划保证金
            position_value: 仓位价值
            symbol_max_leverage: 交易对最大杠杆
            equity: 账户权益
            used_margin: 已用保证金
        
        Returns:
            MarginInfo对象
        """
        # 1. 计算实际杠杆
        actual_leverage = self.calculate_actual_leverage(symbol_max_leverage)
        
        # 2. 计算目标保证金
        target_margin = self.calculate_target_margin(planned_margin, actual_leverage)
        
        # 3. 计算实际保证金
        actual_margin = self.calculate_actual_margin(position_value, actual_leverage)
        
        # 4. 计算保证金维持率
        margin_ratio = self.calculate_margin_ratio(equity, used_margin)
        
        # 5. 检查是否安全
        is_at_risk, _ = self.check_liquidation_risk(equity, used_margin)
        is_safe = not is_at_risk
        
        return MarginInfo(
            actual_leverage=actual_leverage,
            target_margin=target_margin,
            actual_margin=actual_margin,
            margin_ratio=margin_ratio,
            is_safe=is_safe
        )


class SlippageFeeCalculator:
    """
    滑点和手续费计算器
    """
    
    def __init__(self, config: Dict):
        """
        初始化计算器
        
        Args:
            config: 配置参数
                {
                    "slippage_percent": 0.1,  # 滑点百分比
                    "taker_fee": 0.04,  # Taker手续费 (%)
                    "maker_fee": 0.02  # Maker手续费 (%)
                }
        """
        self.slippage_percent = config.get("slippage_percent", 0.1)
        self.taker_fee = config.get("taker_fee", 0.04)
        self.maker_fee = config.get("maker_fee", 0.02)
        
        logger.info(f"✅ 滑点手续费计算器初始化: 滑点={self.slippage_percent}%, Taker={self.taker_fee}%")
    
    def calculate_slippage(self, price: float, is_buy: bool) -> float:
        """
        计算滑点后的实际成交价
        
        Args:
            price: 预期价格
            is_buy: 是否买入
        
        Returns:
            实际成交价
        """
        slippage_amount = price * (self.slippage_percent / 100)
        
        if is_buy:
            # 买入时价格上滑
            actual_price = price + slippage_amount
        else:
            # 卖出时价格下滑
            actual_price = price - slippage_amount
        
        logger.debug(f"📊 滑点计算: 预期={price:.2f}, 实际={actual_price:.2f}, 滑点={slippage_amount:.2f}")
        
        return actual_price
    
    def calculate_fee(self, position_value: float, is_taker: bool = True) -> float:
        """
        计算交易手续费
        
        Args:
            position_value: 仓位价值
            is_taker: 是否Taker订单
        
        Returns:
            手续费金额
        """
        fee_rate = self.taker_fee if is_taker else self.maker_fee
        fee_amount = position_value * (fee_rate / 100)
        
        logger.debug(f"💰 手续费: 仓位价值={position_value:.2f}, 费率={fee_rate}%, 手续费={fee_amount:.2f}")
        
        return fee_amount
    
    def calculate_total_cost(
        self,
        price: float,
        quantity: float,
        is_buy: bool,
        is_taker: bool = True
    ) -> Tuple[float, float, float, float]:
        """
        计算总成本（含滑点和手续费）
        
        Args:
            price: 预期价格
            quantity: 数量
            is_buy: 是否买入
            is_taker: 是否Taker订单
        
        Returns:
            (实际成交价, 仓位价值, 手续费, 总成本)
        """
        # 1. 计算滑点后的实际价格
        actual_price = self.calculate_slippage(price, is_buy)
        
        # 2. 计算仓位价值
        position_value = actual_price * quantity
        
        # 3. 计算手续费
        fee = self.calculate_fee(position_value, is_taker)
        
        # 4. 计算总成本
        total_cost = position_value + fee
        
        logger.info(
            f"📊 总成本计算: "
            f"预期价={price:.2f}, "
            f"实际价={actual_price:.2f}, "
            f"数量={quantity:.6f}, "
            f"仓位价值={position_value:.2f}, "
            f"手续费={fee:.2f}, "
            f"总成本={total_cost:.2f}"
        )
        
        return actual_price, position_value, fee, total_cost


# 示例使用
if __name__ == "__main__":
    print("\n=== 杠杆管理测试 ===")
    
    config = {
        "group_leverage": 10,
        "maintenance_margin_ratio": 0.5
    }
    
    manager = LeverageManager(config)
    
    # 测试杠杆降级
    actual_lev = manager.calculate_actual_leverage(symbol_max_leverage=5)
    print(f"实际杠杆: {actual_lev}x")
    
    # 测试目标保证金
    target_margin = manager.calculate_target_margin(planned_margin=1000, actual_leverage=actual_lev)
    print(f"目标保证金: {target_margin:.2f}")
    
    # 测试保证金维持率
    margin_ratio = manager.calculate_margin_ratio(equity=10000, used_margin=8000)
    print(f"保证金维持率: {margin_ratio:.2f}%")
    
    # 测试爆仓风险
    at_risk, ratio = manager.check_liquidation_risk(equity=10000, used_margin=25000)
    print(f"爆仓风险: {at_risk}, 维持率: {ratio:.2f}%")
    
    print("\n=== 滑点手续费测试 ===")
    
    calc_config = {
        "slippage_percent": 0.1,
        "taker_fee": 0.04,
        "maker_fee": 0.02
    }
    
    calculator = SlippageFeeCalculator(calc_config)
    
    # 测试总成本计算
    actual_price, pos_value, fee, total = calculator.calculate_total_cost(
        price=50000,
        quantity=0.1,
        is_buy=True,
        is_taker=True
    )
    print(f"实际价={actual_price:.2f}, 仓位价值={pos_value:.2f}, 手续费={fee:.2f}, 总成本={total:.2f}")
