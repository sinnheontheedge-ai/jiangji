# 军工级极限审计报告 - 第1部分：数据库层

## 审计时间
2026-02-21

## 审计范围
/tmp/v8_check/v8_docker/backend/core/database.py 及所有访问数据库的代码

---

## 一、ORM字段比对

### ✅ 已修复字段
1. **Instance表**
   - ✅ `use_step_locking` (已存在于ORM)
   - ✅ `step_config` (已存在于ORM)
   - ❌ 业务代码中未发现 `enable_step_lock` 或 `step_lock_config` 错误调用

2. **Order表**
   - ✅ `client_order_id` (已添加到ORM, UNIQUE索引)
   - ✅ `exchange_order_id` (已存在, UNIQUE索引)
   - ✅ `filled_quantity` (已添加到ORM)
   - ✅ `average_price` (已添加到ORM)
   - ✅ `reduce_only` (已添加到ORM)

3. **Position表**
   - ✅ `UNIQUE(instance_id, symbol)` (已添加单仓模式约束)

---

## 二、字段访问验证

### ✅ 正确访问
- `backend/api/instances.py`: 访问 `instance.use_step_locking`, `instance.step_config` ✅
- `backend/tests/test_step_lock.py`: 访问 `instance.step_config` ✅
- `backend/api/orders.py`: 访问 `order.exchange_order_id` ✅
- `backend/core/order_monitor.py`: 访问 `order.exchange_order_id` ✅
- `backend/core/websocket_event_bridge.py`: 访问 `Order.exchange_order_id` ✅
- `backend/core/mock/mock_exchange.py`: 使用 `client_order_ids` 集合 ✅
- `backend/plugins/execution_engine/order_executor.py`: 访问 `order.exchange_order_id`, `order.filled_quantity`, `order.avg_price` ✅

### ❌ 未访问的新字段
- ❌ **Order.client_order_id**: 虽然已添加到ORM，但业务代码中**未找到任何写入逻辑**
- ❌ **Order.filled_quantity**: 只在 `order_executor.py` 中模拟使用，**真实下单链路未写入**
- ❌ **Order.average_price**: 只在 `order_executor.py` 中模拟使用，**真实下单链路未写入**
- ❌ **Order.reduce_only**: 虽然传递给交易所，但**未写入数据库记录**

---

## 三、Decimal精度验证

### ✅ 已修复为Decimal/Numeric
- ✅ `Account.initial_balance`: Numeric(20, 8)
- ✅ `Account.current_balance`: Numeric(20, 8)
- ✅ `FundConfig.initial_capital`: Numeric(20, 8)
- ✅ `FundConfig.compound_ratio`: Numeric(10, 4)
- ✅ `FundConfig.current_base`: Numeric(20, 8)
- ✅ `Order.quantity`: Numeric(20, 8)
- ✅ `Order.filled_quantity`: Numeric(20, 8)
- ✅ `Order.price`: Numeric(20, 8)
- ✅ `Order.average_price`: Numeric(20, 8)
- ✅ `Position.quantity`: Numeric(20, 8)
- ✅ `Position.entry_price`: Numeric(20, 8)
- ✅ `Position.current_price`: Numeric(20, 8)
- ✅ `Position.unrealized_pnl`: Numeric(20, 8)
- ✅ `Position.take_profit`: Numeric(20, 8)
- ✅ `Position.stop_loss`: Numeric(20, 8)
- ✅ `PositionStepLock.peak_price`: Numeric(20, 8)

### ❌ 业务代码中仍使用float
**文件**: `backend/core/binance_client.py`
- ❌ 第85-88行: `float(usdt_asset.get('walletBalance', 0))`
- ❌ 第97-98行: `float(balance.get('USDT', {}).get('total', 0))`
- ❌ 第154-159行: `float(pos.get('contracts', 0))`, `float(pos.get('entryPrice', 0))`
- ❌ 第366-370行: `float(row[1])` (K线数据)

**文件**: `backend/core/binance_websocket.py`
- ❌ 第397-401行: `float(kline['o'])`, `float(kline['h'])` (K线数据)
- ❌ 第428-429行: `float(data['c'])`, `float(data['v'])` (价格数据)
- ❌ 第573-574行: `float(balance.get("wb", 0))` (余额数据)
- ❌ 第591-593行: `float(position.get("pa", 0))` (持仓数据)
- ❌ 第634-635行: `float(order.get("q", 0))` (订单数据)

**文件**: `backend/core/websocket_event_bridge.py`
- ❌ 第156行: `float(mark_price)`

**文件**: `backend/core/trading_safety.py`
- ❌ 第70行: `abs(float(exchange_position.get('contracts', 0)))`

**风险**: 所有从交易所获取的数据都用float处理，会导致**精度丢失**，在高频交易或大额交易中可能产生累计误差。

---

## 四、唯一索引验证

### ✅ 已添加唯一索引
- ✅ `Order.client_order_id`: UNIQUE索引 (idx_client_order_id)
- ✅ `Order.exchange_order_id`: UNIQUE索引 (idx_exchange_order_id)
- ✅ `Position (instance_id, symbol)`: UNIQUE约束 (uq_instance_symbol)

### ❌ 缺少数据库migration脚本
- ❌ 修改了ORM定义，但**未提供migration脚本**
- ❌ 现有数据库不会自动添加这些索引
- ❌ 如果数据库中已有重复数据，添加索引会失败

---

## 五、事务控制验证

### ✅ 已使用事务的地方
- ✅ `backend/core/database.py`: `get_db()` 使用 `try-except-rollback-finally` ✅
- ✅ `backend/api/instances.py`: `create_instance` 使用 `await db.commit()` 和 `await db.rollback()` ✅
- ✅ `backend/api/orders.py`: `cancel_order` 使用 `await db.commit()` 和 `await db.rollback()` ✅
- ✅ `backend/api/positions.py`: `close_position` 使用 `await db.commit()` 和 `await db.rollback()` ✅

### ❌ 缺少事务控制的地方
**文件**: `backend/core/trade_executor.py`
- ❌ `_execute_trade` 方法: 下单成功后写入DB，但**未使用事务包裹整个流程**
- ❌ 如果下单成功但DB写入失败，会导致**订单泄漏**（交易所有订单，数据库无记录）
- ❌ **未实现撤单补偿机制**

**文件**: `backend/plugins/execution_engine/order_executor.py`
- ❌ `_submit_to_exchange` 方法: 更新 `order.exchange_order_id` 后未立即commit
- ❌ 如果后续流程失败，exchange_order_id可能丢失

---

## 六、阻塞问题清单

### 🔴 P0级阻塞（必须修复）

1. **Order.client_order_id未写入数据库**
   - 位置: 所有下单链路
   - 风险: 幂等性无法验证，重试会重复下单
   - 必须: 在所有下单函数中写入client_order_id到数据库

2. **Order.filled_quantity/average_price/reduce_only未写入数据库**
   - 位置: 所有下单和成交回报处理
   - 风险: 部分成交无法追踪，平仓记录不完整
   - 必须: 成交回报处理时更新这些字段

3. **业务代码大量使用float**
   - 位置: binance_client.py, binance_websocket.py, websocket_event_bridge.py, trading_safety.py
   - 风险: 精度丢失，累计误差
   - 必须: 全部改为Decimal

4. **缺少数据库migration脚本**
   - 位置: migrations目录
   - 风险: 现有数据库无法升级，索引不生效
   - 必须: 提供Alembic migration脚本

5. **下单成功但DB写入失败无补偿**
   - 位置: trade_executor.py
   - 风险: 订单泄漏，资金风险
   - 必须: 实现撤单补偿机制

---

## 七、最终结论

❌ **数据库层不可实盘运行**

**原因**:
1. 幂等性字段未写入数据库（P0）
2. 大量float精度问题（P0）
3. 缺少migration脚本（P0）
4. 缺少撤单补偿机制（P0）
5. 部分成交字段未追踪（P0）

**必须修复所有P0问题才能进入下一阶段审计。**
