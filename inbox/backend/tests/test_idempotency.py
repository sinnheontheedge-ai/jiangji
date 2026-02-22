"""
测试: 幂等性 - 防止重复下单 (P0一票否决)
"""
import pytest
import uuid


@pytest.mark.asyncio
async def test_duplicate_client_order_id_should_return_same_order(mock_client):
    """测试: 重复的clientOrderId应该返回相同订单"""
    client_order_id = str(uuid.uuid4())
    
    # 第一次下单
    order1 = await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        reduce_only=False,
        client_order_id=client_order_id
    )
    
    # 第二次用相同clientOrderId下单
    order2 = await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        reduce_only=False,
        client_order_id=client_order_id
    )
    
    # 应该返回相同订单
    assert order1['id'] == order2['id']
    assert order1['clientOrderId'] == order2['clientOrderId']
    
    # 验证只有一笔成交
    position = mock_client.get_position("BTC/USDT")
    assert position['quantity'] == 0.01  # 只有一次成交


@pytest.mark.asyncio
async def test_retry_with_same_client_order_id(mock_client_with_failures):
    """测试: 网络重试时使用相同clientOrderId"""
    client_order_id = str(uuid.uuid4())
    max_retries = 5
    order = None
    
    for attempt in range(max_retries):
        try:
            order = await mock_client_with_failures.create_market_order(
                symbol="BTC/USDT",
                side="buy",
                amount=0.01,
                reduce_only=False,
                client_order_id=client_order_id
            )
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            continue
    
    assert order is not None
    assert order['clientOrderId'] == client_order_id
    
    # 验证只有一笔成交
    position = mock_client_with_failures.get_position("BTC/USDT")
    assert position['quantity'] == 0.01


@pytest.mark.asyncio
async def test_different_client_order_id_creates_new_order(mock_client):
    """测试: 不同的clientOrderId创建新订单"""
    # 第一笔订单
    order1 = await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        reduce_only=False,
        client_order_id=str(uuid.uuid4())
    )
    
    # 第二笔订单（不同clientOrderId）
    order2 = await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        reduce_only=False,
        client_order_id=str(uuid.uuid4())
    )
    
    # 应该是不同订单
    assert order1['id'] != order2['id']
    assert order1['clientOrderId'] != order2['clientOrderId']
    
    # 验证有两笔成交
    position = mock_client.get_position("BTC/USDT")
    assert position['quantity'] == 0.02


@pytest.mark.asyncio
async def test_limit_order_idempotency(mock_client):
    """测试: 限价单的幂等性"""
    client_order_id = str(uuid.uuid4())
    
    # 第一次下限价单
    order1 = await mock_client.create_limit_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        price=49000.0,
        reduce_only=False,
        client_order_id=client_order_id
    )
    
    # 第二次用相同clientOrderId
    order2 = await mock_client.create_limit_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        price=49000.0,
        reduce_only=False,
        client_order_id=client_order_id
    )
    
    # 应该返回相同订单
    assert order1['id'] == order2['id']
