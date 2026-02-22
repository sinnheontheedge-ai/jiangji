"""
测试: StepLock档位触发、持久化和重启恢复
"""
import pytest
from core.database import Position, PositionStepLock, Instance, Strategy, Account
from core.step_lock_manager import StepLockCoordinator
from plugins.risk_engine.tpsl_manager import PositionSide
from sqlalchemy import select


@pytest.mark.asyncio
async def test_step_lock_initialization(db_session):
    """测试: StepLock初始化"""
    # 创建测试数据
    account = Account(name="Test", api_key="key", api_secret="secret", testnet=True)
    db_session.add(account)
    
    strategy = Strategy(name="Test", description="Test", code="pass")
    db_session.add(strategy)
    
    instance = Instance(
        name="Test",
        account_id=1,
        strategy_id=1,
        symbols=["BTC/USDT"],
        timeframe="1h",
        position_mode="single",
        use_step_locking=True,
        step_config={
            "levels": [
                {"threshold_pct": 5, "lock_pct": 2},
                {"threshold_pct": 10, "lock_pct": 5},
                {"threshold_pct": 15, "lock_pct": 8}
            ]
        }
    )
    db_session.add(instance)
    await db_session.commit()
    
    # 创建持仓
    position = Position(
        instance_id=instance.id,
        symbol="BTC/USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        is_open=True
    )
    db_session.add(position)
    await db_session.commit()
    await db_session.refresh(position)
    
    # 初始化StepLock
    coordinator = StepLockCoordinator(db_session)
    success = await coordinator.initialize_step_lock(
        position_id=position.id,
        entry_price=50000.0,
        side="LONG",
        step_lock_config=instance.step_config
    )
    
    assert success is True
    
    # 验证数据库记录
    result = await db_session.execute(
        select(PositionStepLock).where(PositionStepLock.position_id == position.id)
    )
    step_lock = result.scalar_one()
    
    assert step_lock.current_level == 0
    assert step_lock.peak_price == 50000.0
    assert len(step_lock.levels_config) == 3


@pytest.mark.asyncio
async def test_step_lock_trigger(db_session):
    """测试: StepLock档位触发"""
    # 创建测试数据
    account = Account(name="Test", api_key="key", api_secret="secret", testnet=True)
    db_session.add(account)
    
    strategy = Strategy(name="Test", description="Test", code="pass")
    db_session.add(strategy)
    
    instance = Instance(
        name="Test",
        account_id=1,
        strategy_id=1,
        symbols=["BTC/USDT"],
        timeframe="1h",
        position_mode="single",
        use_step_locking=True,
        step_config={
            "levels": [
                {"threshold_pct": 5, "lock_pct": 2},
                {"threshold_pct": 10, "lock_pct": 5}
            ]
        }
    )
    db_session.add(instance)
    await db_session.commit()
    
    position = Position(
        instance_id=instance.id,
        symbol="BTC/USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        is_open=True
    )
    db_session.add(position)
    await db_session.commit()
    await db_session.refresh(position)
    
    # 初始化StepLock
    coordinator = StepLockCoordinator(db_session)
    await coordinator.initialize_step_lock(
        position_id=position.id,
        entry_price=50000.0,
        side="LONG",
        step_lock_config=instance.step_config
    )
    
    # 价格上涨5%，触发第一档
    current_price = 52500.0  # 50000 * 1.05
    trigger_result = await coordinator.check_and_trigger_step_lock(
        position_id=position.id,
        current_price=current_price
    )
    
    assert trigger_result is not None
    assert trigger_result['triggered'] is True
    assert trigger_result['new_level'] == 1
    assert trigger_result['new_sl_price'] > 50000.0
    
    # 验证数据库更新
    result = await db_session.execute(
        select(PositionStepLock).where(PositionStepLock.position_id == position.id)
    )
    step_lock = result.scalar_one()
    assert step_lock.current_level == 1
    assert step_lock.peak_price == current_price


@pytest.mark.asyncio
async def test_step_lock_no_skip_levels(db_session):
    """测试: StepLock不允许跳级"""
    # 创建测试数据
    account = Account(name="Test", api_key="key", api_secret="secret", testnet=True)
    db_session.add(account)
    
    strategy = Strategy(name="Test", description="Test", code="pass")
    db_session.add(strategy)
    
    instance = Instance(
        name="Test",
        account_id=1,
        strategy_id=1,
        symbols=["BTC/USDT"],
        timeframe="1h",
        position_mode="single",
        use_step_locking=True,
        step_config={
            "levels": [
                {"threshold_pct": 5, "lock_pct": 2},
                {"threshold_pct": 10, "lock_pct": 5},
                {"threshold_pct": 15, "lock_pct": 8}
            ]
        }
    )
    db_session.add(instance)
    await db_session.commit()
    
    position = Position(
        instance_id=instance.id,
        symbol="BTC/USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        is_open=True
    )
    db_session.add(position)
    await db_session.commit()
    await db_session.refresh(position)
    
    coordinator = StepLockCoordinator(db_session)
    await coordinator.initialize_step_lock(
        position_id=position.id,
        entry_price=50000.0,
        side="LONG",
        step_lock_config=instance.step_config
    )
    
    # 价格直接上涨15%（应该只触发第一档，不跳级）
    current_price = 57500.0  # 50000 * 1.15
    trigger_result = await coordinator.check_and_trigger_step_lock(
        position_id=position.id,
        current_price=current_price
    )
    
    # 应该触发第一档
    assert trigger_result['new_level'] == 1
    
    # 再次检查，应该触发第二档
    trigger_result = await coordinator.check_and_trigger_step_lock(
        position_id=position.id,
        current_price=current_price
    )
    
    assert trigger_result['new_level'] == 2


@pytest.mark.asyncio
async def test_step_lock_recovery_after_restart(db_session):
    """测试: StepLock重启后恢复"""
    # 创建测试数据
    account = Account(name="Test", api_key="key", api_secret="secret", testnet=True)
    db_session.add(account)
    
    strategy = Strategy(name="Test", description="Test", code="pass")
    db_session.add(strategy)
    
    instance = Instance(
        name="Test",
        account_id=1,
        strategy_id=1,
        symbols=["BTC/USDT"],
        timeframe="1h",
        position_mode="single",
        use_step_locking=True,
        step_config={
            "levels": [
                {"threshold_pct": 5, "lock_pct": 2},
                {"threshold_pct": 10, "lock_pct": 5}
            ]
        }
    )
    db_session.add(instance)
    await db_session.commit()
    
    position = Position(
        instance_id=instance.id,
        symbol="BTC/USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        is_open=True
    )
    db_session.add(position)
    await db_session.commit()
    position_id = position.id
    
    # 初始化并触发第一档
    coordinator = StepLockCoordinator(db_session)
    await coordinator.initialize_step_lock(
        position_id=position_id,
        entry_price=50000.0,
        side="LONG",
        step_lock_config=instance.step_config
    )
    
    await coordinator.check_and_trigger_step_lock(
        position_id=position_id,
        current_price=52500.0
    )
    
    # 模拟重启：创建新的coordinator
    new_coordinator = StepLockCoordinator(db_session)
    
    # 获取状态
    state = await new_coordinator.get_step_lock_state(position_id)
    
    assert state is not None
    assert state['current_level'] == 1
    assert state['peak_price'] == 52500.0
    
    # 继续触发第二档
    trigger_result = await new_coordinator.check_and_trigger_step_lock(
        position_id=position_id,
        current_price=55000.0
    )
    
    assert trigger_result['new_level'] == 2
