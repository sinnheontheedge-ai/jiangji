"""
pytest配置和共享fixtures
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.database import Base
from core.mock.mock_binance_client import MockBinanceClient


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    """创建测试数据库会话"""
    # 使用内存SQLite数据库
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def mock_client():
    """创建Mock交易所客户端"""
    client = MockBinanceClient(
        testnet=True,
        network_fail_rate=0.0,
        timeout_rate=0.0,
        partial_fill_rate=0.0,
        log_file="logs/test_exchange_call.jsonl"
    )
    yield client
    client.reset()


@pytest.fixture
def mock_client_with_failures():
    """创建带故障模拟的Mock客户端"""
    client = MockBinanceClient(
        testnet=True,
        network_fail_rate=0.1,
        timeout_rate=0.1,
        partial_fill_rate=0.2,
        log_file="logs/test_exchange_call_failures.jsonl"
    )
    yield client
    client.reset()
