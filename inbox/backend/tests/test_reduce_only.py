"""
测试: 所有平仓订单必须reduceOnly=True (P0一票否决)
"""
import pytest
from core.mock.mock_exchange import MockExchangeError


@pytest.mark.asyncio
async def test_close_position_must_have_reduce_only(mock_client):
    """测试: 平仓订单必须设置reduceOnly=True"""
    # 先开仓
    await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        reduce_only=False
    )
    
    # 验证持仓存在
    position = mock_client.get_position("BTC/USDT")
    assert position is not None
    assert position['quantity'] > 0
    
    # 平仓必须设置reduceOnly=True
    close_order = await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="sell",
        amount=0.01,
        reduce_only=True
    )
    
    assert close_order['reduceOnly'] is True
    assert close_order['status'] == 'closed'


@pytest.mark.asyncio
async def test_reduce_only_without_position_should_fail(mock_client):
    """测试: reduceOnly订单在无持仓时应该失败"""
    with pytest.raises(MockExchangeError, match="无持仓"):
        await mock_client.create_market_order(
            symbol="BTC/USDT",
            side="sell",
            amount=0.01,
            reduce_only=True
        )


@pytest.mark.asyncio
async def test_reduce_only_wrong_direction_should_fail(mock_client):
    """测试: reduceOnly订单方向错误应该失败"""
    # 做多持仓
    await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        reduce_only=False
    )
    
    # 尝试用buy平仓（应该失败）
    with pytest.raises(MockExchangeError, match="方向错误"):
        await mock_client.create_market_order(
            symbol="BTC/USDT",
            side="buy",
            amount=0.01,
            reduce_only=True
        )


@pytest.mark.asyncio
async def test_stop_loss_must_have_reduce_only(mock_client):
    """测试: 止损订单必须设置reduceOnly=True"""
    # 开仓
    await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        reduce_only=False
    )
    
    # 止损限价单必须reduceOnly=True
    stop_order = await mock_client.create_limit_order(
        symbol="BTC/USDT",
        side="sell",
        amount=0.01,
        price=49000.0,
        reduce_only=True,
        params={"reason": "stop_loss"}
    )
    
    assert stop_order['reduceOnly'] is True


@pytest.mark.asyncio
async def test_take_profit_must_have_reduce_only(mock_client):
    """测试: 止盈订单必须设置reduceOnly=True"""
    # 开仓
    await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        reduce_only=False
    )
    
    # 止盈限价单必须reduceOnly=True
    tp_order = await mock_client.create_limit_order(
        symbol="BTC/USDT",
        side="sell",
        amount=0.01,
        price=51000.0,
        reduce_only=True,
        params={"reason": "take_profit"}
    )
    
    assert tp_order['reduceOnly'] is True


@pytest.mark.asyncio
async def test_step_lock_triggered_close_must_have_reduce_only(mock_client):
    """测试: StepLock触发的平仓必须设置reduceOnly=True"""
    # 开仓
    await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        reduce_only=False
    )
    
    # StepLock触发平仓
    step_lock_order = await mock_client.create_market_order(
        symbol="BTC/USDT",
        side="sell",
        amount=0.01,
        reduce_only=True,
        params={"reason": "step_lock_triggered", "source": "StepLockManager"}
    )
    
    assert step_lock_order['reduceOnly'] is True
