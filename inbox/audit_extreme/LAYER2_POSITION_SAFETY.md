# 第2层审计：仓位安全

## 1. 列出所有下单函数

### 下单函数定义
**文件**: `core/binance_client.py`
- 行195-233: `create_market_order`
- 行235-295: `create_limit_order`
- 行297-?: `create_stop_market_order` (**未找到定义**)

### 下单函数调用（共10处）
1. **api/positions.py:160** - 平仓调用
2. **core/trade_executor.py:369** - 开仓调用
3. **core/trade_executor.py:417** - 止盈订单
4. **core/trade_executor.py:428** - 止损订单 (**调用不存在的函数**)
5. **core/risk_monitor.py:349** - 更新止损 (**调用不存在的函数**)
6. **core/risk_monitor.py:433** - 更新止损 (**调用不存在的函数**)
7. **plugins/execution_engine/order_executor.py:389** - 市价单
8. **plugins/execution_engine/order_executor.py:396** - 限价单
9. **plugins/execution_engine/order_executor.py:489** - 演示代码
10. **tests/test_reduce_only.py** - 测试代码（多处）

---

## 2. 是否统一入口

### ❌ 无统一入口

**下单入口（至少4个）**:
1. **api/positions.py:160** - API直接调用binance_client
2. **core/trade_executor.py:369** - 执行器调用binance_client
3. **core/risk_monitor.py:349** - 风控监控器调用binance_client
4. **plugins/execution_engine/order_executor.py:389** - 插件调用binance_client

**问题**:
1. 下单逻辑分散在4个不同模块
2. **无统一入口**
3. **无法统一控制**
4. **无法统一审计**
5. **风险：绕过安全检查**

---

## 3. clientOrderId是否强制生成

### ✅ binance_client中已强制生成
**文件**: `core/binance_client.py`
- 行209-212: 市价单clientOrderId生成
- 行260-263: 限价单clientOrderId生成

**代码**:
```python
# 行209-212
if 'clientOrderId' not in params:
    client_order_id = str(uuid.uuid4())
    params['clientOrderId'] = client_order_id
    logger.warning(f"⚠️ 未提供clientOrderId，自动生成: {client_order_id}")
```

### ⚠️ 但调用方未传递clientOrderId
**文件**: `api/positions.py:160`
```python
order_result = await client.create_market_order(
    symbol=position.symbol,
    side="SELL" if position.side == "LONG" else "BUY",
    amount=abs(position.quantity),
    reduce_only=True
)
# 未传递clientOrderId参数
```

**文件**: `core/trade_executor.py:369`
```python
order_result = await client.create_market_order(
    symbol=signal['symbol'],
    side=signal['side'],
    amount=quantity
)
# 未传递clientOrderId参数
```

**问题**:
1. binance_client会自动生成UUID
2. 但**UUID是随机的，无业务含义**
3. **无法通过clientOrderId追踪订单来源**
4. **无法防止业务层重复下单**

**正确做法**:
```python
client_order_id = f"open_{instance_id}_{timestamp}_{uuid}"
order_result = await client.create_market_order(
    ...,
    params={'clientOrderId': client_order_id}
)
```

---

## 4. client_order_id是否UNIQUE

### ✅ 数据库已定义UNIQUE约束
**文件**: `core/database.py`
- 行175: `Index('idx_client_order_id', 'client_order_id', unique=True)`
- 行183: `client_order_id = Column(String(100), unique=True, nullable=False, ...)`

**结论**: ✅ 数据库层已保证UNIQUE

---

## 5. exchange_order_id是否UNIQUE

### ✅ 数据库已定义UNIQUE约束
**文件**: `core/database.py`
- 行176: `Index('idx_exchange_order_id', 'exchange_order_id', unique=True)`
- 行184: `exchange_order_id = Column(String(100), unique=True, ...)`

**结论**: ✅ 数据库层已保证UNIQUE

---

## 6. 单仓模式数据库唯一约束

### ✅ 数据库已定义UNIQUE约束
**文件**: `core/database.py`
- 行202: `UniqueConstraint('instance_id', 'symbol', name='uq_instance_symbol')`

**结论**: ✅ 数据库层已保证单仓模式

---

## 7. reduceOnly=True是否强制

### ⚠️ 部分强制，部分未强制

#### ✅ 已强制的地方
**文件**: `api/positions.py:160-165`
```python
order_result = await client.create_market_order(
    symbol=position.symbol,
    side="SELL" if position.side == "LONG" else "BUY",
    amount=abs(position.quantity),
    reduce_only=True  # ✅ 强制
)
```

**文件**: `core/binance_client.py:214-219`
```python
if reduce_only:
    params['reduceOnly'] = True
    logger.info(f"✅ 平仓订单: reduceOnly=True")
else:
    logger.info(f"📝 开仓订单: reduceOnly=False")
```

#### ❌ 未强制的地方
**文件**: `core/trade_executor.py:369-373`
```python
order_result = await client.create_market_order(
    symbol=signal['symbol'],
    side=signal['side'],
    amount=quantity
)
# ❌ 未传递reduce_only参数
```

**文件**: `core/trade_executor.py:417-421`
```python
tp_order_result = await client.create_limit_order(
    symbol=signal['symbol'],
    side="SELL" if signal['side'] == "BUY" else "BUY",
    amount=quantity,
    price=tp_price
)
# ❌ 止盈订单未设置reduceOnly
```

**文件**: `core/trade_executor.py:428-433`
```python
sl_order_result = await client.create_stop_market_order(  # ❌ 函数不存在
    symbol=signal['symbol'],
    side="SELL" if signal['side'] == "BUY" else "BUY",
    amount=quantity,
    stop_price=sl_price
)
# ❌ 止损订单未设置reduceOnly
```

**文件**: `core/risk_monitor.py:349-354`
```python
new_sl_order = await client.create_stop_market_order(  # ❌ 函数不存在
    symbol=position.symbol,
    side="SELL" if position.side == "LONG" else "BUY",
    amount=abs(position.quantity),
    stop_price=new_sl_price
)
# ❌ 止损订单未设置reduceOnly
```

**问题**:
1. 平仓API（api/positions.py）强制了reduceOnly
2. 但**trade_executor中的止盈止损订单未设置reduceOnly**
3. 但**risk_monitor中的止损更新未设置reduceOnly**
4. **风险：止盈止损可能开新仓**

---

## 8. 网络重试是否可能重复下单

### ❌ 存在重复下单风险

**文件**: `core/binance_client.py:195-233`
```python
async def create_market_order(self, symbol, side, amount, reduce_only=False, params=None):
    try:
        # ...生成clientOrderId...
        order = await self.exchange.create_market_order(...)
        return order
    except Exception as e:
        logger.error(f"❌ 创建市价单失败: {e}")
        raise
```

**问题**:
1. 异常后直接raise
2. **无重试机制**
3. **如果调用方重试，会生成新的clientOrderId**
4. **导致重复下单**

**场景**:
```
1. 调用create_market_order，生成clientOrderId=UUID1
2. 网络超时，抛出异常
3. 调用方捕获异常，重试
4. 再次调用create_market_order，生成clientOrderId=UUID2
5. 两个订单都提交到交易所
6. 重复下单
```

**正确做法**:
```python
# 调用方应该传递固定的clientOrderId
client_order_id = f"open_{instance_id}_{timestamp}"
for retry in range(3):
    try:
        order = await client.create_market_order(
            ...,
            params={'clientOrderId': client_order_id}  # 固定的ID
        )
        break
    except Exception as e:
        if retry == 2:
            raise
        # 重试前先查询订单是否已存在
        existing_order = await client.fetch_order_by_client_order_id(client_order_id)
        if existing_order:
            return existing_order
```

---

## 9. DB写入失败是否补偿

### ❌ 无补偿机制

**文件**: `core/trade_executor.py:369-529`
```python
# 行369-373: 下单
order_result = await client.create_market_order(...)

# 行505-527: DB写入
order = Order(...)
position = Position(...)
self.db.add(order)
self.db.add(position)

# 行529: commit
await self.db.commit()
```

**问题**:
1. 先下单（行369）
2. 再DB写入（行505-527）
3. 再commit（行529）
4. **如果commit失败，订单已提交但DB无记录**
5. **无补偿机制撤销订单**
6. **订单泄漏**

**风险场景**:
```
1. 下单成功，订单ID=12345
2. DB写入order和position
3. commit失败（数据库连接断开）
4. 订单12345已在交易所，但DB无记录
5. 系统不知道这个订单的存在
6. 订单可能成交，但系统不知道
7. 持仓状态错误
```

**正确做法**:
```python
try:
    # 1. DB写入
    order = Order(...)
    db.add(order)
    await db.commit()
    
    # 2. 下单
    order_result = await client.create_market_order(...)
    
    # 3. 更新订单状态
    order.exchange_order_id = order_result['id']
    order.status = "SUBMITTED"
    await db.commit()
except Exception as e:
    # 如果下单失败，删除DB记录
    await db.rollback()
    raise
```

或者使用SAGA模式：
```python
saga = SagaOrchestrator("place_order")
saga.add_step(
    action=lambda: db_write_order(),
    compensation=lambda: db_delete_order()
)
saga.add_step(
    action=lambda: exchange_place_order(),
    compensation=lambda: exchange_cancel_order()
)
await saga.execute()
```

---

## 10. 列出任何可能导致仓位翻倍的路径

### 🔴 风险路径1: 重复下单
**原因**: 网络重试生成新clientOrderId
**位置**: binance_client.py:209-212
**场景**: 
```
1. 下单超时
2. 重试，生成新UUID
3. 两个订单都成交
4. 仓位翻倍
```

### 🔴 风险路径2: 单仓模式未在下单前检查
**文件**: `core/trade_executor.py:421-550`
**代码**:
```python
# 行439-454: 单仓模式检查
if instance.position_mode == "single":
    existing_positions = await self.db.execute(
        select(Position).where(
            Position.instance_id == instance_id,
            Position.status == "open"
        )
    )
    existing = existing_positions.scalars().first()
    if existing:
        # 拒绝开仓
        ...
```

**问题**:
1. 单仓模式检查在代码中存在（行439-454）
2. 但**_execute_trade永远不被调用**
3. **单仓模式检查永远不生效**
4. **如果有其他下单路径，会绕过检查**

**实际情况**:
- api/positions.py:160 直接调用binance_client，**绕过单仓检查**
- plugins/execution_engine/order_executor.py:389 直接调用binance_client，**绕过单仓检查**

### 🔴 风险路径3: 数据库唯一约束失效
**文件**: `core/database.py:202`
```python
UniqueConstraint('instance_id', 'symbol', name='uq_instance_symbol')
```

**问题**:
1. 数据库有唯一约束
2. 但**如果下单成功但DB写入失败**
3. **数据库无记录，约束不生效**
4. **下次下单仍然会成功**
5. **仓位翻倍**

### 🔴 风险路径4: 止盈止损未设置reduceOnly
**位置**: trade_executor.py:417, 428
**问题**:
1. 止盈止损订单未设置reduceOnly
2. **如果持仓已平，止盈止损触发会开新仓**
3. **仓位翻倍**

---

## 11. 最终结论

### ❌ 第2层审计失败：仓位安全无法保证

**失败原因**:
1. **无统一下单入口**（4个入口）
2. **clientOrderId未传递业务ID**（无法防止业务层重复）
3. **网络重试会重复下单**（生成新UUID）
4. **DB写入失败无补偿**（订单泄漏）
5. **止盈止损未设置reduceOnly**（可能开新仓）
6. **单仓模式检查不生效**（_execute_trade永远不被调用）
7. **多个下单路径绕过安全检查**

**具体文件+行号**:
- binance_client.py:209-212 - 自动生成UUID，无业务含义
- trade_executor.py:369 - 未传递clientOrderId
- trade_executor.py:417, 428 - 止盈止损未设置reduceOnly
- trade_executor.py:428 - 调用不存在的create_stop_market_order
- trade_executor.py:369-529 - 先下单后DB写入，无补偿
- api/positions.py:160 - 绕过trade_executor直接下单
- plugins/execution_engine/order_executor.py:389 - 绕过trade_executor直接下单
- risk_monitor.py:349, 433 - 调用不存在的create_stop_market_order

**系统判定**: 
# ❌ 系统不可实盘
# 原因：存在多个仓位翻倍风险路径，无统一下单入口，无补偿机制，止盈止损可能开新仓
