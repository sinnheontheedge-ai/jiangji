"""
测试: 实例启停生命周期
"""
import pytest
from core.database import Instance, InstanceStatus, Strategy, Account
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_instance(db_session):
    """测试: 创建实例"""
    # 创建测试账户
    account = Account(
        name="Test Account",
        api_key="test_key",
        api_secret="test_secret",
        testnet=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    
    # 创建测试策略
    strategy = Strategy(
        name="TestStrategy",
        description="Test",
        code="class TestStrategy: pass"
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    
    # 创建实例
    instance = Instance(
        name="Test Instance",
        account_id=account.id,
        strategy_id=strategy.id,
        symbols=["BTC/USDT"],
        timeframe="1h",
        position_mode="single",
        use_step_locking=False,
        status=InstanceStatus.IDLE.value
    )
    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)
    
    assert instance.id is not None
    assert instance.status == InstanceStatus.IDLE.value


@pytest.mark.asyncio
async def test_start_instance(db_session):
    """测试: 启动实例"""
    # 创建账户和策略
    account = Account(
        name="Test Account",
        api_key="test_key",
        api_secret="test_secret",
        testnet=True
    )
    db_session.add(account)
    
    strategy = Strategy(
        name="TestStrategy",
        description="Test",
        code="class TestStrategy: pass"
    )
    db_session.add(strategy)
    await db_session.commit()
    
    # 创建实例
    instance = Instance(
        name="Test Instance",
        account_id=account.id,
        strategy_id=strategy.id,
        symbols=["BTC/USDT"],
        timeframe="1h",
        position_mode="single",
        status=InstanceStatus.IDLE.value
    )
    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)
    
    # 启动实例
    instance.status = InstanceStatus.RUNNING.value
    await db_session.commit()
    
    # 验证状态
    result = await db_session.execute(
        select(Instance).where(Instance.id == instance.id)
    )
    updated_instance = result.scalar_one()
    assert updated_instance.status == InstanceStatus.RUNNING.value


@pytest.mark.asyncio
async def test_stop_instance(db_session):
    """测试: 停止实例"""
    # 创建账户和策略
    account = Account(
        name="Test Account",
        api_key="test_key",
        api_secret="test_secret",
        testnet=True
    )
    db_session.add(account)
    
    strategy = Strategy(
        name="TestStrategy",
        description="Test",
        code="class TestStrategy: pass"
    )
    db_session.add(strategy)
    await db_session.commit()
    
    # 创建运行中的实例
    instance = Instance(
        name="Test Instance",
        account_id=account.id,
        strategy_id=strategy.id,
        symbols=["BTC/USDT"],
        timeframe="1h",
        position_mode="single",
        status=InstanceStatus.RUNNING.value
    )
    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)
    
    # 停止实例
    instance.status = InstanceStatus.STOPPED.value
    await db_session.commit()
    
    # 验证状态
    result = await db_session.execute(
        select(Instance).where(Instance.id == instance.id)
    )
    updated_instance = result.scalar_one()
    assert updated_instance.status == InstanceStatus.STOPPED.value


@pytest.mark.asyncio
async def test_instance_state_persistence(db_session):
    """测试: 实例状态持久化"""
    # 创建账户和策略
    account = Account(
        name="Test Account",
        api_key="test_key",
        api_secret="test_secret",
        testnet=True
    )
    db_session.add(account)
    
    strategy = Strategy(
        name="TestStrategy",
        description="Test",
        code="class TestStrategy: pass"
    )
    db_session.add(strategy)
    await db_session.commit()
    
    # 创建实例
    instance = Instance(
        name="Test Instance",
        account_id=account.id,
        strategy_id=strategy.id,
        symbols=["BTC/USDT"],
        timeframe="1h",
        position_mode="single",
        status=InstanceStatus.IDLE.value
    )
    db_session.add(instance)
    await db_session.commit()
    instance_id = instance.id
    
    # 模拟重启：重新查询
    result = await db_session.execute(
        select(Instance).where(Instance.id == instance_id)
    )
    reloaded_instance = result.scalar_one()
    
    assert reloaded_instance.id == instance_id
    assert reloaded_instance.status == InstanceStatus.IDLE.value
    assert reloaded_instance.symbols == ["BTC/USDT"]
