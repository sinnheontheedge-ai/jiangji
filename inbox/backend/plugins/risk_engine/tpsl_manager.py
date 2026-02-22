"""
止盈止损管理器 - 完整实现
支持固定TP/SL、移动止损和分档锁盈
"""
from typing import Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from loguru import logger


class PositionSide(str, Enum):
    """仓位方向"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class TPSLPrices:
    """止盈止损价格"""
    tp_price: float  # 止盈价格
    sl_price: float  # 止损价格
    trailing_sl: Optional[float] = None  # 移动止损价格


@dataclass
class StepLockLevel:
    """分档锁盈档位"""
    level: int  # 档位编号
    threshold_pct: float  # 触发阈值百分比
    lock_pct: float  # 锁盈百分比
    threshold_price: float  # 触发价格
    lock_price: float  # 锁盈价格


class TPSLManager:
    """
    止盈止损管理器
    
    实现完整的TP/SL数学公式
    """
    
    def __init__(self, config: Dict):
        """
        初始化TP/SL管理器
        
        Args:
            config: 配置参数
                {
                    "tp_percent": 5.0,  # 止盈百分比
                    "sl_percent": 2.0,  # 止损百分比
                    "enable_trailing": False,  # 是否启用移动止损
                    "trailing_percent": 1.0  # 移动止损百分比
                }
        """
        self.tp_percent = config.get("tp_percent", 5.0)
        self.sl_percent = config.get("sl_percent", 2.0)
        self.enable_trailing = config.get("enable_trailing", False)
        self.trailing_percent = config.get("trailing_percent", 1.0)
        
        logger.info(f"✅ TP/SL管理器初始化: TP={self.tp_percent}%, SL={self.sl_percent}%")
    
    def calculate_tpsl(self, entry_price: float, side: PositionSide) -> TPSLPrices:
        """
        计算止盈止损价格（核心方法）
        
        公式：
        做多 (Long):
            TP_price = P_entry * (1 + TP_pct / 100)
            SL_price_init = P_entry * (1 - SL_pct / 100)
        
        做空 (Short):
            TP_price = P_entry * (1 - TP_pct / 100)
            SL_price_init = P_entry * (1 + SL_pct / 100)
        
        Args:
            entry_price: 进场价格 P_entry
            side: 仓位方向
        
        Returns:
            TPSLPrices对象
        """
        if side == PositionSide.LONG:
            # 做多
            tp_price = entry_price * (1 + self.tp_percent / 100)
            sl_price = entry_price * (1 - self.sl_percent / 100)
            logger.debug(f"📊 做多TP/SL: 进场={entry_price:.2f}, TP={tp_price:.2f}, SL={sl_price:.2f}")
        else:
            # 做空
            tp_price = entry_price * (1 - self.tp_percent / 100)
            sl_price = entry_price * (1 + self.sl_percent / 100)
            logger.debug(f"📊 做空TP/SL: 进场={entry_price:.2f}, TP={tp_price:.2f}, SL={sl_price:.2f}")
        
        return TPSLPrices(tp_price=tp_price, sl_price=sl_price)
    
    def update_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        side: PositionSide,
        peak_price: Optional[float] = None,
        trough_price: Optional[float] = None
    ) -> Optional[float]:
        """
        更新移动止损价格
        
        公式：
        做多 (Long):
            Trailing_SL = P_peak * (1 - Trail_pct / 100)
        
        做空 (Short):
            Trailing_SL = P_trough * (1 + Trail_pct / 100)
        
        Args:
            entry_price: 进场价格
            current_price: 当前价格
            side: 仓位方向
            peak_price: 开仓后最高价 (做多使用)
            trough_price: 开仓后最低价 (做空使用)
        
        Returns:
            移动止损价格，如果未启用则返回None
        """
        if not self.enable_trailing:
            return None
        
        if side == PositionSide.LONG:
            # 做多：使用最高价计算移动止损
            if peak_price is None:
                peak_price = max(entry_price, current_price)
            else:
                peak_price = max(peak_price, current_price)
            
            trailing_sl = peak_price * (1 - self.trailing_percent / 100)
            logger.debug(f"📈 做多移动止损: 峰值={peak_price:.2f}, Trailing_SL={trailing_sl:.2f}")
            return trailing_sl
        
        else:
            # 做空：使用最低价计算移动止损
            if trough_price is None:
                trough_price = min(entry_price, current_price)
            else:
                trough_price = min(trough_price, current_price)
            
            trailing_sl = trough_price * (1 + self.trailing_percent / 100)
            logger.debug(f"📉 做空移动止损: 谷底={trough_price:.2f}, Trailing_SL={trailing_sl:.2f}")
            return trailing_sl
    
    def check_stop_triggered(
        self,
        current_price: float,
        tp_price: float,
        sl_price: float,
        side: PositionSide
    ) -> Tuple[bool, str]:
        """
        检查是否触发止盈或止损
        
        Args:
            current_price: 当前价格
            tp_price: 止盈价格
            sl_price: 止损价格
            side: 仓位方向
        
        Returns:
            (是否触发, 触发类型: "TP" | "SL" | "")
        """
        if side == PositionSide.LONG:
            # 做多
            if current_price >= tp_price:
                logger.info(f"✅ 触发止盈: 当前价={current_price:.2f} >= TP={tp_price:.2f}")
                return True, "TP"
            elif current_price <= sl_price:
                logger.warning(f"❌ 触发止损: 当前价={current_price:.2f} <= SL={sl_price:.2f}")
                return True, "SL"
        else:
            # 做空
            if current_price <= tp_price:
                logger.info(f"✅ 触发止盈: 当前价={current_price:.2f} <= TP={tp_price:.2f}")
                return True, "TP"
            elif current_price >= sl_price:
                logger.warning(f"❌ 触发止损: 当前价={current_price:.2f} >= SL={sl_price:.2f}")
                return True, "SL"
        
        return False, ""


class StepLockManager:
    """
    分档锁盈管理器
    
    实现完整的Step Lock数学公式
    """
    
    def __init__(self, config: Dict):
        """
        初始化分档锁盈管理器
        
        Args:
            config: 配置参数
                {
                    "levels": [
                        {"threshold_pct": 2.0, "lock_pct": 1.0},  # 第1档
                        {"threshold_pct": 5.0, "lock_pct": 3.0},  # 第2档
                        {"threshold_pct": 10.0, "lock_pct": 7.0}  # 第3档
                    ]
                }
        """
        self.levels_config = config.get("levels", [])
        
        if not self.levels_config:
            logger.warning("⚠️ 未配置分档锁盈档位")
        else:
            logger.info(f"✅ 分档锁盈管理器初始化: {len(self.levels_config)}个档位")
    
    def calculate_levels(self, entry_price: float, side: PositionSide) -> List[StepLockLevel]:
        """
        计算所有档位的触发价格和锁盈价格
        
        公式：
        做多 (Long):
            触发价格: Level_n = P_entry * (1 + Threshold_pct_n / 100)
            锁盈价格: SL_lock_n = P_entry * (1 + Lock_pct_n / 100)
        
        做空 (Short):
            触发价格: Level_n = P_entry * (1 - Threshold_pct_n / 100)
            锁盈价格: SL_lock_n = P_entry * (1 - Lock_pct_n / 100)
        
        Args:
            entry_price: 进场价格 P_entry
            side: 仓位方向
        
        Returns:
            档位列表
        """
        levels = []
        
        for i, level_config in enumerate(self.levels_config, start=1):
            threshold_pct = level_config["threshold_pct"]
            lock_pct = level_config["lock_pct"]
            
            if side == PositionSide.LONG:
                # 做多
                threshold_price = entry_price * (1 + threshold_pct / 100)
                lock_price = entry_price * (1 + lock_pct / 100)
            else:
                # 做空
                threshold_price = entry_price * (1 - threshold_pct / 100)
                lock_price = entry_price * (1 - lock_pct / 100)
            
            level = StepLockLevel(
                level=i,
                threshold_pct=threshold_pct,
                lock_pct=lock_pct,
                threshold_price=threshold_price,
                lock_price=lock_price
            )
            levels.append(level)
            
            logger.debug(f"档位{i}: 触发={threshold_price:.2f}, 锁盈={lock_price:.2f}")
        
        return levels
    
    def check_level_triggered(
        self,
        current_price: float,
        levels: List[StepLockLevel],
        current_level: int,
        side: PositionSide
    ) -> Tuple[bool, int, Optional[float]]:
        """
        检查是否触发新的锁盈档位
        
        Args:
            current_price: 当前价格 P_last
            levels: 所有档位
            current_level: 当前档位（0表示未触发任何档位）
            side: 仓位方向
        
        Returns:
            (是否触发新档位, 新档位编号, 新的锁盈止损价)
        """
        for level in levels:
            # 只检查比当前档位更高的档位
            if level.level <= current_level:
                continue
            
            # 检查触发条件
            triggered = False
            if side == PositionSide.LONG:
                # 做多: P_last >= threshold_price
                triggered = current_price >= level.threshold_price
            else:
                # 做空: P_last <= threshold_price
                triggered = current_price <= level.threshold_price
            
            if triggered:
                logger.info(
                    f"🔒 触发第{level.level}档锁盈: "
                    f"当前价={current_price:.2f}, "
                    f"锁盈价={level.lock_price:.2f}"
                )
                return True, level.level, level.lock_price
        
        return False, current_level, None
    
    def calculate_effective_sl(
        self,
        initial_sl: float,
        lock_sl: Optional[float],
        side: PositionSide
    ) -> float:
        """
        计算有效止损价格
        
        公式：
        做多 (Long): max(SL_price_init, SL_lock)
        做空 (Short): min(SL_price_init, SL_lock)
        
        Args:
            initial_sl: 初始止损价格
            lock_sl: 锁盈止损价格
            side: 仓位方向
        
        Returns:
            有效止损价格
        """
        if lock_sl is None:
            return initial_sl
        
        if side == PositionSide.LONG:
            # 做多：取较高的止损价
            effective_sl = max(initial_sl, lock_sl)
        else:
            # 做空：取较低的止损价
            effective_sl = min(initial_sl, lock_sl)
        
        logger.debug(f"有效止损: 初始={initial_sl:.2f}, 锁盈={lock_sl:.2f}, 有效={effective_sl:.2f}")
        return effective_sl


# 示例使用
if __name__ == "__main__":
    print("\n=== TP/SL测试 ===")
    
    config_tpsl = {
        "tp_percent": 5.0,
        "sl_percent": 2.0,
        "enable_trailing": True,
        "trailing_percent": 1.0
    }
    
    manager = TPSLManager(config_tpsl)
    
    # 测试做多
    entry = 50000
    tpsl = manager.calculate_tpsl(entry, PositionSide.LONG)
    print(f"做多: 进场={entry}, TP={tpsl.tp_price:.2f}, SL={tpsl.sl_price:.2f}")
    
    # 测试移动止损
    trailing = manager.update_trailing_stop(entry, 52000, PositionSide.LONG, peak_price=52500)
    print(f"移动止损: {trailing:.2f}")
    
    print("\n=== 分档锁盈测试 ===")
    
    config_step = {
        "levels": [
            {"threshold_pct": 2.0, "lock_pct": 1.0},
            {"threshold_pct": 5.0, "lock_pct": 3.0},
            {"threshold_pct": 10.0, "lock_pct": 7.0}
        ]
    }
    
    step_manager = StepLockManager(config_step)
    levels = step_manager.calculate_levels(entry, PositionSide.LONG)
    
    for level in levels:
        print(f"档位{level.level}: 触发={level.threshold_price:.2f}, 锁盈={level.lock_price:.2f}")
    
    # 测试触发检查
    current_price = 51500
    triggered, new_level, lock_price = step_manager.check_level_triggered(
        current_price, levels, 0, PositionSide.LONG
    )
    print(f"\n当前价={current_price}, 触发={triggered}, 档位={new_level}, 锁盈价={lock_price}")
