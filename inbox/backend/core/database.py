"""
数据库配置和模型定义
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Numeric, Index, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from enum import Enum
from decimal import Decimal
import os

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://trading_bot:trading_bot_password@localhost:5432/trading_bot")

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# 创建异步会话工厂
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# 创建基类
Base = declarative_base()


# ==================== 依赖注入 ====================

async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ==================== 枚举类型 ====================

class InstanceStatus(str, Enum):
    """实例状态"""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


# ==================== 数据库模型 ====================

class Account(Base):
    """账户表"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="账户名称")
    exchange = Column(String(50), nullable=False, comment="交易所")
    api_key = Column(String(200), nullable=False, comment="API Key")
    api_secret = Column(String(200), nullable=False, comment="API Secret")
    testnet = Column(Boolean, default=False, comment="是否使用测试网")
    proxy_config = Column(JSON, comment="代理配置 {host, port}")
    initial_balance = Column(Numeric(20, 8), nullable=False, default=0.0, comment="初始金额")
    current_balance = Column(Numeric(20, 8), nullable=False, default=0.0, comment="当前余额")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联资金管理配置
    fund_config = relationship("FundConfig", back_populates="account", uselist=False, cascade="all, delete-orphan")


class FundConfig(Base):
    """资金管理配置表"""
    __tablename__ = "fund_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False, comment="关联账户ID")
    
    # 全局配置
    initial_capital = Column(Numeric(20, 8), nullable=False, default=1000.0, comment="全局初始投入金额")
    
    # 复利配置
    compounding_mode = Column(String(20), nullable=False, default="stage", comment="复利模式: stage/perpetual")
    compound_ratio = Column(Numeric(10, 4), nullable=False, default=20.0, comment="复利比例 (%)")
    current_base = Column(Numeric(20, 8), nullable=False, default=1000.0, comment="当前复利起点")
    
    # 盈利提取配置
    extraction_mode = Column(String(20), nullable=False, default="wallet_threshold", comment="提取模式: wallet_threshold/multiple_mode")
    threshold = Column(Float, nullable=True, comment="提取阈值(钱包阈值模式)")
    multiple = Column(Float, nullable=True, comment="提取倍数(倍数模式)")
    
    # 初始金额保护配置
    enable_initial_protect = Column(Boolean, default=False, comment="是否启用初始金额保护")
    protect_multiplier = Column(Float, nullable=True, comment="保护倍数")
    max_protect_count = Column(Integer, nullable=True, comment="最大保护次数")
    protect_count = Column(Integer, default=0, comment="已执行保护次数")
    last_protect_balance = Column(Float, nullable=True, comment="上次保护后的余额")
    
    # 盈利倍数终点配置
    enable_endpoint = Column(Boolean, default=False, comment="是否启用盈利倍数终点")
    endpoint_multiplier = Column(Float, nullable=True, comment="终点倍数（无上限）")
    endpoint_count = Column(Integer, default=0, comment="终点触发次数（循环执行）")
    
    # 自动补足余额配置
    enable_replenish = Column(Boolean, default=False, comment="是否启用自动补足余额")
    replenish_min_amount = Column(Float, nullable=True, default=10, comment="最小转账金额")
    replenish_enable_alert = Column(Boolean, default=True, comment="启用余额不足告警")
    replenish_alert_threshold = Column(Float, nullable=True, default=0.8, comment="告警阈值(百分比)")
    replenish_max_per_day = Column(Integer, nullable=True, comment="每日最大补足次数（无上限）")
    total_replenished_amount = Column(Float, default=0.0, comment="累计补足金额（未覆盖部分）")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    account = relationship("Account", back_populates="fund_config")


class Strategy(Base):
    """策略表"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, comment="策略名称")
    description = Column(Text, comment="策略描述")
    code = Column(Text, nullable=False, comment="策略代码")
    parameters = Column(JSON, comment="策略参数")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Instance(Base):
    """实例表"""
    __tablename__ = "instances"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="实例名称")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="关联账户")
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False, comment="关联策略")
    symbols = Column(JSON, nullable=False, comment="交易对列表")
    timeframe = Column(String(20), nullable=False, comment="时间周期")
    take_profit = Column(Float, comment="止盈百分比")
    stop_loss = Column(Float, comment="止损百分比")
    position_mode = Column(String(20), default="single", comment="仓位模式: single/multiple")
    use_step_locking = Column(Boolean, default=False, comment="是否使用分档锁盈")
    step_config = Column(JSON, comment="分档锁盈配置")
    enable_trailing_stop = Column(Boolean, default=False, comment="是否启用移动止损")
    trailing_stop_percent = Column(Float, comment="移动止损百分比")
    leverage = Column(Integer, default=10, comment="杠杆倍数")
    status = Column(String(20), default=InstanceStatus.IDLE.value, comment="实例状态")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    """订单表"""
    __tablename__ = "orders"
    __table_args__ = (
        Index('idx_client_order_id', 'client_order_id', unique=True),
        Index('idx_exchange_order_id', 'exchange_order_id', unique=True),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="账户ID")
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True, comment="关联持仓ID")
    client_order_id = Column(String(100), unique=True, nullable=False, comment="客户端订单ID(幂等性键)")
    exchange_order_id = Column(String(100), unique=True, comment="交易所订单ID")
    symbol = Column(String(50), nullable=False, comment="交易对")
    side = Column(String(10), nullable=False, comment="方向: BUY/SELL")
    order_type = Column(String(20), nullable=False, comment="订单类型")
    quantity = Column(Numeric(20, 8), nullable=False, comment="数量")
    filled_quantity = Column(Numeric(20, 8), default=0.0, comment="已成交数量")
    price = Column(Numeric(20, 8), comment="价格")
    average_price = Column(Numeric(20, 8), comment="平均成交价")
    reduce_only = Column(Boolean, default=False, comment="是否仅减仓")
    status = Column(String(20), nullable=False, comment="订单状态")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Position(Base):
    """持仓表"""
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint('instance_id', 'symbol', name='uq_instance_symbol'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="账户ID")
    symbol = Column(String(50), nullable=False, comment="交易对")
    side = Column(String(10), nullable=False, comment="方向: LONG/SHORT")
    quantity = Column(Numeric(20, 8), nullable=False, comment="持仓数量")
    entry_price = Column(Numeric(20, 8), nullable=False, comment="开仓价格")
    current_price = Column(Numeric(20, 8), comment="当前价格")
    unrealized_pnl = Column(Numeric(20, 8), default=0.0, comment="未实现盈亏")
    leverage = Column(Integer, default=1, comment="杠杆倍数")
    take_profit = Column(Numeric(20, 8), comment="止盈价格")
    stop_loss = Column(Numeric(20, 8), comment="止损价格")
    is_open = Column(Boolean, default=True, comment="是否持仓中")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PositionStepLock(Base):
    """持仓Step Lock状态表"""
    __tablename__ = "position_step_locks"
    
    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), unique=True, nullable=False, comment="持仓ID")
    current_level = Column(Integer, default=0, comment="当前档位（0表示未触发任何档位）")
    levels_config = Column(JSON, comment="档位配置JSON")
    peak_price = Column(Numeric(20, 8), comment="峰值价格")
    last_check_time = Column(DateTime, comment="上次检查时间")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    position = relationship("Position", backref="step_lock")


class Notification(Base):
    """通知配置表"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, comment="通知类型: telegram/email/webhook")
    config = Column(JSON, nullable=False, comment="通知配置")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, comment="配置键")
    value = Column(Text, nullable=False, comment="配置值(JSON格式)")
    description = Column(Text, comment="配置描述")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class StateTransition(Base):
    """状态转换历史表"""
    __tablename__ = "state_transitions"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, comment="实体类型（instance/order/position）")
    entity_id = Column(Integer, nullable=False, comment="实体ID")
    from_state = Column(String(50), comment="源状态")
    to_state = Column(String(50), nullable=False, comment="目标状态")
    reason = Column(Text, comment="转换原因")
    extra_data = Column(JSON, comment="附加元数据（JSON格式）")
    created_at = Column(DateTime, default=datetime.utcnow)


class IdempotencyKey(Base):
    """幂等性键表"""
    __tablename__ = "idempotency_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, comment="幂等性键")
    response = Column(Text, comment="缓存的响应")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, comment="过期时间")


class SagaLog(Base):
    """Saga日志表"""
    __tablename__ = "saga_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    saga_id = Column(String(100), nullable=False, comment="Saga ID")
    step_name = Column(String(100), nullable=False, comment="步骤名称")
    status = Column(String(20), nullable=False, comment="状态: pending/completed/failed/compensated")
    input_data = Column(JSON, comment="输入数据")
    output_data = Column(JSON, comment="输出数据")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationConfig(Base):
    """通知配置表（与notification_configs表对应）"""
    __tablename__ = "notification_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="配置名称")
    type = Column(String(50), nullable=False, comment="通知类型: telegram/email/webhook/dingtalk/wechat")
    config = Column(JSON, nullable=False, comment="通知配置")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
