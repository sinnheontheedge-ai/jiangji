"""
更新后的FundConfig数据库模型
根据需求文档修改字段
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class FundConfig(Base):
    """资金管理配置表（更新后）"""
    __tablename__ = "fund_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False, comment="关联账户ID")
    
    # ========================================
    # 全局配置
    # ========================================
    initial_capital = Column(Float, nullable=False, default=1000.0, comment="全局初始投入金额")
    
    # ========================================
    # 复利配置
    # ========================================
    compounding_mode = Column(String(20), nullable=False, default="stage", comment="复利模式: stage/perpetual")
    compound_ratio = Column(Float, nullable=False, default=20.0, comment="复利比例 (%)")
    current_base = Column(Float, nullable=False, default=1000.0, comment="当前复利起点")
    
    # ❌ 删除: position_percent - 移到实例管理
    # ❌ 删除: concurrent_positions - 移到实例管理
    # ❌ 删除: initial_base - 使用 initial_capital
    
    # ========================================
    # 盈利提取配置
    # ========================================
    extraction_mode = Column(String(20), nullable=False, default="wallet_threshold", comment="提取模式: wallet_threshold/multiple_mode")
    threshold = Column(Float, nullable=True, comment="提取阈值(钱包阈值模式)")
    multiple = Column(Float, nullable=True, comment="提取倍数(倍数模式)")
    
    # ❌ 删除: initial_margin - 使用 initial_capital
    # ❌ 删除: max_extract_ratio - 无意义
    
    # ========================================
    # 初始金额保护配置
    # ========================================
    enable_initial_protect = Column(Boolean, default=False, comment="是否启用初始金额保护")
    protect_multiplier = Column(Float, nullable=True, comment="保护倍数")
    max_protect_count = Column(Integer, nullable=True, comment="最大保护次数")
    protect_count = Column(Integer, default=0, comment="已执行保护次数")
    last_protect_balance = Column(Float, nullable=True, comment="上次保护后的余额")
    
    # ❌ 删除: protection_initial_amount - 使用 initial_capital
    # ❌ 删除: protection_transfer_step - 无意义
    # ✅ 重命名: protection_enabled → enable_initial_protect
    # ✅ 重命名: protection_multiple → protect_multiplier
    # ✅ 重命名: protection_max_count → max_protect_count
    # ✅ 重命名: protection_count → protect_count
    # ✅ 新增: last_protect_balance
    
    # ========================================
    # 盈利倍数终点配置
    # ========================================
    enable_endpoint = Column(Boolean, default=False, comment="是否启用盈利倍数终点")
    endpoint_multiplier = Column(Float, nullable=True, comment="终点倍数（无上限）")
    endpoint_count = Column(Integer, default=0, comment="终点触发次数（循环执行）")
    
    # ❌ 删除: endpoint_initial_amount - 使用 initial_capital
    # ❌ 删除: endpoint_transfer_step - 无意义
    # ✅ 重命名: endpoint_enabled → enable_endpoint
    # ✅ 重命名: endpoint_multiple → endpoint_multiplier
    # ✅ 修改: endpoint_triggered → endpoint_count（改为计数器）
    
    # ========================================
    # 自动补足余额配置
    # ========================================
    enable_replenish = Column(Boolean, default=False, comment="是否启用自动补足余额")
    replenish_min_amount = Column(Float, nullable=True, default=10, comment="最小转账金额")
    replenish_enable_alert = Column(Boolean, default=True, comment="启用余额不足告警")
    replenish_alert_threshold = Column(Float, nullable=True, default=0.8, comment="告警阈值(百分比)")
    replenish_max_per_day = Column(Integer, nullable=True, comment="每日最大补足次数（无上限）")
    
    # ❌ 删除: replenish_initial_capital - 使用 initial_capital
    # ❌ 删除: replenish_check_interval - 使用WebSocket
    # ✅ 重命名: replenish_enabled → enable_replenish
    
    # ========================================
    # 时间戳
    # ========================================
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    account = relationship("Account", back_populates="fund_config")


# ========================================
# 字段变更总结
# ========================================
# 
# 删除字段（9个）:
# 1. initial_base - 与initial_capital重复
# 2. position_percent - 移到实例管理
# 3. concurrent_positions - 移到实例管理
# 4. initial_margin - 使用initial_capital
# 5. max_extract_ratio - 无意义
# 6. protection_initial_amount - 使用initial_capital
# 7. protection_transfer_step - 无意义
# 8. endpoint_initial_amount - 使用initial_capital
# 9. endpoint_transfer_step - 无意义
# 10. replenish_initial_capital - 使用initial_capital
# 11. replenish_check_interval - 使用WebSocket
# 
# 新增字段（3个）:
# 1. initial_capital - 全局初始投入金额
# 2. protect_count - 初始金额保护已触发次数
# 3. last_protect_balance - 上次保护后的余额
# 
# 重命名字段（8个）:
# 1. protection_enabled → enable_initial_protect
# 2. protection_multiple → protect_multiplier
# 3. protection_max_count → max_protect_count
# 4. protection_count → protect_count
# 5. endpoint_enabled → enable_endpoint
# 6. endpoint_multiple → endpoint_multiplier
# 7. endpoint_triggered → endpoint_count
# 8. replenish_enabled → enable_replenish
# 
# 修改约束（2个）:
# 1. endpoint_multiplier - 移除上限约束
# 2. replenish_max_per_day - 移除上限约束
# ========================================
