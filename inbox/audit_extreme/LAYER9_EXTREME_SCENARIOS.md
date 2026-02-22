# 第9层审计：极端场景

## 1. 网络抖动重试是否重复下单

### 网络重试逻辑
**文件**: `core/binance_client.py:create_market_order, create_limit_order`

#### 当前实现
```python
async def create_market_order(self, symbol, side, amount, reduce_only=False, client_order_id=None):
    # 如果未提供clientOrderId，自动生成
    if not client_order_id:
        client_order_id = str(uuid.uuid4())
        logger.warning(f"⚠️ 未提供clientOrderId，自动生成: {client_order_id}")
    
    # 下单
    order = await self.client.create_order(
        symbol=symbol,
        side=side,
        type='MARKET',
        quantity=amount,
        reduceOnly=reduce_only,
        newClientOrderId=client_order_id  # ✅ 使用clientOrderId
    )
```

### 问题分析

#### 场景1：网络超时重试
```
1. 调用方生成UUID: "abc-123"
2. 第1次下单: clientOrderId="abc-123" → 网络超时
3. 调用方重试，生成新UUID: "def-456"  # ❌ 问题
4. 第2次下单: clientOrderId="def-456" → 成功
5. 结果: 可能下单2次（如果第1次实际成功）
```

### ❌ P0-33: 网络重试会重复下单
**文件**: `binance_client.py:create_market_order, create_limit_order`
**问题**: 
1. 调用方每次生成新UUID
2. 网络超时重试时使用新UUID
3. 如果第1次实际成功，会下单2次

**影响**: 
- **仓位翻倍风险**
- **资金安全风险**

**正确做法**:
```python
# 调用方应该固定clientOrderId
client_order_id = f"open_{instance_id}_{position_id}_{timestamp}"
# 重试时使用相同的client_order_id
```

---

## 2. WebSocket断线是否状态错乱

### WebSocket重连机制
**文件**: `core/binance_websocket.py`

#### 搜索重连逻辑
```bash
grep -n "reconnect\|retry" backend/core/binance_websocket.py
# 结果：无匹配
```

### ❌ P0-34: WebSocket无重连机制
**文件**: `binance_websocket.py`
**问题**: 
- 未找到重连逻辑
- WebSocket断线后不会自动重连

**影响**: 
- **行情数据断流**
- **成交回报丢失**
- **状态错乱**

---

### EventBus WebSocket断线
**文件**: `core/event_bus.py`

#### Redis连接检查
```bash
grep -n "redis\|Redis" backend/core/event_bus.py
# 结果：无匹配（使用内存EventBus）
```

### ❌ P0-35: EventBus使用内存版本，无持久化
**文件**: `event_bus.py`
**问题**: 
- 使用内存EventBus
- 无Redis持久化
- 进程重启后事件丢失

**影响**: 
- **事件丢失**
- **状态不一致**

---

## 3. 数据库写入失败是否补偿

### 下单后DB写入失败
**文件**: `core/trade_executor.py:_execute_trade`

#### 当前实现
```python
# 1. 下单
order_result = await client.create_market_order(...)

# 2. 写入数据库
new_order = Order(...)
db.add(new_order)
await db.commit()  # ❌ 如果这里失败，订单已经下了但DB没记录
```

### ❌ P0-36: 下单成功但DB写入失败无补偿
**文件**: `trade_executor.py:_execute_trade`
**问题**: 
1. 下单成功
2. DB写入失败（网络/磁盘/约束冲突）
3. 订单已在交易所，但DB无记录

**影响**: 
- **订单泄漏**
- **持仓不一致**
- **资金不一致**

**正确做法**:
```python
try:
    # 1. 下单
    order_result = await client.create_market_order(...)
    
    # 2. 写入数据库
    new_order = Order(...)
    db.add(new_order)
    await db.commit()
except Exception as e:
    # 3. DB写入失败，撤单补偿
    try:
        await client.cancel_order(order_result['orderId'])
        logger.error("DB写入失败，已撤单补偿")
    except:
        logger.critical("撤单补偿失败，订单泄漏！")
    raise
```

---

## 4. 强平行情是否安全

### 强平触发逻辑
**文件**: `core/risk_monitor.py:_check_stop_loss, _check_take_profit`

#### 当前实现
```python
async def _check_stop_loss(self, position: Position, current_price: float):
    # 检查止损
    if should_stop_loss:
        # 下单平仓
        await client.create_stop_market_order(...)  # ❌ 函数不存在
```

### ❌ P0-11: 调用不存在的函数（重复）
**文件**: `risk_monitor.py:349, 433`
**问题**: 调用create_stop_market_order，但函数不存在
**影响**: 
- **强平失败**
- **系统崩溃**

---

### 强平订单reduceOnly
**文件**: `core/risk_monitor.py:_check_stop_loss`

#### 当前实现
```python
await client.create_stop_market_order(
    symbol=position.symbol,
    side="sell" if position.side == "LONG" else "buy",
    amount=abs(position.amount),
    stop_price=position.stop_loss,
    # ❌ 未设置reduce_only=True
)
```

### ❌ P0-37: 强平订单未设置reduceOnly
**文件**: `risk_monitor.py:349, 433`
**问题**: 强平订单未设置reduce_only=True
**影响**: 
- **可能开新仓**
- **仓位翻倍**

---

## 5. 多实例并发是否冲突

### 单仓模式检查
**文件**: `core/trade_executor.py:_execute_trade`

#### 当前实现
```python
# 检查单仓模式
existing_positions = await db.execute(
    select(Position).where(
        Position.instance_id == instance_id,
        Position.symbol == signal.symbol,
        Position.is_open == True
    )
)
existing_position = existing_positions.scalar_one_or_none()

if existing_position:
    logger.warning("单仓模式：已有持仓，拒绝开仓")
    return
```

### ❌ P0-38: 单仓模式检查无数据库约束
**文件**: `database.py:Position`
**问题**: 
- 代码层检查单仓模式
- 数据库无UNIQUE约束
- 并发情况下可能同时开仓

**影响**: 
- **多实例并发冲突**
- **单仓模式失效**

**正确做法**:
```python
# 数据库添加唯一索引
Index('idx_unique_open_position', 'instance_id', 'symbol', 'is_open', unique=True)
```

---

## 6. 其他极端场景

### 场景1：部分成交
**文件**: `websocket_event_bridge.py:on_user_data_event`

#### 当前实现
```python
if event_type == 'ORDER_TRADE_UPDATE':
    # 更新订单状态
    order.status = order_data.get('X')  # FILLED/PARTIALLY_FILLED
    
    # 更新持仓
    if order.status == 'FILLED':
        position.amount += order.amount  # ✅ 全部成交
    # ❌ 部分成交未处理
```

### ❌ P0-39: 部分成交未处理
**文件**: `websocket_event_bridge.py:on_user_data_event`
**问题**: 
- 只处理FILLED状态
- PARTIALLY_FILLED状态未更新持仓

**影响**: 
- **持仓数量错误**
- **资金不一致**

---

### 场景2：订单取消
**文件**: `websocket_event_bridge.py:on_user_data_event`

#### 当前实现
```python
if event_type == 'ORDER_TRADE_UPDATE':
    order.status = order_data.get('X')  # CANCELED
    await db.commit()
    # ❌ 未处理取消后的持仓恢复
```

### ⚠️ 警告：订单取消后持仓恢复未处理
**影响**: 如果止损单被取消，持仓无保护

---

### 场景3：价格精度错误
**文件**: `core/binance_client.py:create_market_order`

#### 当前实现
```python
order = await self.client.create_order(
    symbol=symbol,
    quantity=amount,  # ❌ 未按exchange filters截断
)
```

### ❌ P0-40: 下单数量未按exchange filters截断
**文件**: `binance_client.py:create_market_order, create_limit_order`
**问题**: 
- 下单数量未按exchange filters截断
- 可能因精度错误被交易所拒绝

**影响**: 
- **下单失败**
- **系统无法交易**

**正确做法**:
```python
# 获取exchange filters
filters = await self.client.get_symbol_info(symbol)
min_qty = filters['minQty']
step_size = filters['stepSize']

# 截断数量
amount = math.floor(amount / step_size) * step_size
if amount < min_qty:
    raise ValueError("数量小于最小下单量")
```

---

## 7. P0阻塞清单

### P0-33: 网络重试会重复下单
**文件**: `binance_client.py`
**问题**: 调用方每次生成新UUID，网络超时重试时使用新UUID
**影响**: 仓位翻倍风险

### P0-34: WebSocket无重连机制
**文件**: `binance_websocket.py`
**问题**: WebSocket断线后不会自动重连
**影响**: 行情数据断流，成交回报丢失，状态错乱

### P0-35: EventBus使用内存版本，无持久化
**文件**: `event_bus.py`
**问题**: 使用内存EventBus，进程重启后事件丢失
**影响**: 事件丢失，状态不一致

### P0-36: 下单成功但DB写入失败无补偿
**文件**: `trade_executor.py:_execute_trade`
**问题**: 下单成功但DB写入失败，无撤单补偿
**影响**: 订单泄漏，持仓不一致，资金不一致

### P0-37: 强平订单未设置reduceOnly
**文件**: `risk_monitor.py:349, 433`
**问题**: 强平订单未设置reduce_only=True
**影响**: 可能开新仓，仓位翻倍

### P0-38: 单仓模式检查无数据库约束
**文件**: `database.py:Position`
**问题**: 代码层检查单仓模式，数据库无UNIQUE约束，并发情况下可能同时开仓
**影响**: 多实例并发冲突，单仓模式失效

### P0-39: 部分成交未处理
**文件**: `websocket_event_bridge.py:on_user_data_event`
**问题**: 只处理FILLED状态，PARTIALLY_FILLED状态未更新持仓
**影响**: 持仓数量错误，资金不一致

### P0-40: 下单数量未按exchange filters截断
**文件**: `binance_client.py:create_market_order, create_limit_order`
**问题**: 下单数量未按exchange filters截断，可能因精度错误被交易所拒绝
**影响**: 下单失败，系统无法交易

---

## 8. 最终结论

### ❌ 第9层审计失败：极端场景存在大量P0阻塞

**失败原因**:
1. **网络重试会重复下单**（仓位翻倍风险）
2. **WebSocket无重连机制**（状态错乱）
3. **EventBus无持久化**（事件丢失）
4. **下单成功但DB写入失败无补偿**（订单泄漏）
5. **强平订单未设置reduceOnly**（仓位翻倍）
6. **单仓模式检查无数据库约束**（并发冲突）
7. **部分成交未处理**（持仓数量错误）
8. **下单数量未按exchange filters截断**（下单失败）

**具体文件+行号**:
- binance_client.py - 网络重试/精度截断
- binance_websocket.py - WebSocket重连
- event_bus.py - EventBus持久化
- trade_executor.py - DB写入失败补偿
- risk_monitor.py:349, 433 - 强平reduceOnly
- database.py:Position - 单仓模式约束
- websocket_event_bridge.py - 部分成交处理

**系统判定**: 
# ❌ 系统不可实盘
# 原因：极端场景存在8个P0阻塞，任何一个都可能导致资金损失或系统崩溃
