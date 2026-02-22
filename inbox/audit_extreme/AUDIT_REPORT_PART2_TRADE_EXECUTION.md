# 军工级极限审计报告 - 第2部分：交易执行层

## 审计时间
2026-02-21

## 审计范围
- `/tmp/v8_check/v8_docker/backend/core/trade_executor.py`
- `/tmp/v8_check/v8_docker/backend/core/binance_client.py`
- `/tmp/v8_check/v8_docker/backend/api/positions.py`
- 所有下单函数调用链

---

## 一、下单函数清单

### 主下单函数
1. **BinanceClient.create_market_order** (binance_client.py:221)
   - 调用: trade_executor.py:369, positions.py:160
   - 参数: symbol, side, amount, reduce_only, client_order_id

2. **BinanceClient.create_limit_order** (binance_client.py:283)
   - 调用: trade_executor.py:417
   - 参数: symbol, side, amount, price, reduce_only, client_order_id

3. **BinanceClient.create_stop_market_order** (binance_client.py:未找到)
   - 调用: trade_executor.py:428
   - ❌ **函数不存在**

---

## 二、reduceOnly强制验证

### ✅ 已强制reduceOnly=True的地方
1. **positions.py:164** - 平仓订单
   ```python
   reduce_only=True,  # P0修复: 平仓必须设置reduceOnly=True
   ```

2. **trade_executor.py:422** - 止盈订单
   ```python
   reduce_only=True
   ```

3. **trade_executor.py:433** - 止损订单
   ```python
   reduce_only=True
   ```

### ✅ 已明确reduceOnly=False的地方
1. **trade_executor.py:373** - 开仓订单
   ```python
   reduce_only=False,  # 开仓订单
   ```

### ❌ 问题
1. **BinanceClient.create_limit_order** (binance_client.py:283)
   - 止盈订单调用时传递了reduce_only=True
   - 但BinanceClient内部**未验证reduce_only参数是否正确传递给交易所**
   - 只记录了日志，未强制校验

2. **create_stop_market_order函数不存在**
   - trade_executor.py:428调用了不存在的函数
   - 止损订单无法下单
   - **系统无法运行**

---

## 三、clientOrderId幂等性验证

### ✅ 已生成clientOrderId的地方
1. **trade_executor.py:362** - 开仓订单
   ```python
   client_order_id = f"open_{instance_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
   ```

2. **positions.py:153** - 平仓订单
   ```python
   client_order_id = f"close_{pos.id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
   ```

### ❌ 未生成clientOrderId的地方
1. **trade_executor.py:417** - 止盈订单
   - ❌ 未传递client_order_id参数
   - 重试会重复下单

2. **trade_executor.py:428** - 止损订单
   - ❌ 未传递client_order_id参数
   - 重试会重复下单

### ❌ clientOrderId未写入数据库
**文件**: `trade_executor.py`
- 第380-391行: 创建Order对象，但**未设置client_order_id字段**
- 第439-451行: 创建止盈Order对象，**未设置client_order_id字段**
- 第454-466行: 创建止损Order对象，**未设置client_order_id字段**

**风险**: 
- 数据库中无法查询clientOrderId
- 无法验证重试是否重复下单
- 幂等性机制失效

---

## 四、网络重试验证

### ❌ 无重试机制
**文件**: `trade_executor.py`
- `_execute_trade`方法: 下单失败后**未重试**
- 如果网络抖动，订单可能失败但不重试
- 如果重试，**未检查订单是否已存在**（因为clientOrderId未写入DB）

### ❌ 重试会导致重复下单
**原因**:
1. 止盈/止损订单未使用clientOrderId
2. 即使使用了clientOrderId，也未写入数据库
3. 重试前无法查询订单是否已存在

**风险**: 网络抖动时，同一个信号可能下多个订单

---

## 五、DB写入失败补偿验证

### ❌ 无撤单补偿机制
**文件**: `trade_executor.py`
- 第369行: `await client.create_market_order(...)` - 下单成功
- 第380-392行: 创建Order对象
- 第469行: `await db.commit()` - 如果commit失败？

**问题**:
1. 下单成功后，如果DB写入失败（网络/数据库故障）
2. 交易所有订单，但数据库无记录
3. **订单泄漏**，无法追踪
4. **未实现撤单补偿**

**正确流程应该是**:
```python
try:
    order_result = await client.create_market_order(...)
    order = Order(...)
    db.add(order)
    await db.commit()
except Exception as e:
    # 补偿: 撤销交易所订单
    await client.cancel_order(order_result['orderId'])
    raise
```

---

## 六、部分成交处理验证

### ❌ 未处理部分成交
**文件**: `trade_executor.py`
- 第389行: `status="FILLED"` - 直接假设订单全部成交
- **未查询实际成交数量**
- **未更新filled_quantity字段**

**文件**: `binance_client.py`
- create_market_order返回订单信息，但**未提取成交数量**
- **未处理部分成交场景**

**风险**:
1. 市价单可能部分成交
2. 持仓数量与实际不符
3. 止盈止损数量错误
4. 平仓时数量不匹配

---

## 七、单仓模式硬拦截验证

### ✅ 已实现单仓模式检查
**文件**: `trade_executor.py`
- 第236-262行: 检查是否已有持仓
- 如有持仓，拒绝开仓并发布trade:rejected事件

### ❌ 问题
1. 第257行: `"size": existing_position.size`
   - Position模型中字段名是`quantity`，不是`size`
   - **字段名错误，会导致KeyError**

---

## 八、事务控制验证

### ⚠️ 部分使用事务
**文件**: `trade_executor.py`
- 第469行: `await db.commit()` - 提交事务
- 但**未使用try-except包裹整个下单流程**
- 下单成功但commit失败时，**未回滚交易所订单**

### ❌ 缺少事务回滚
**问题**:
1. 如果止盈订单下单失败，开仓订单已成交
2. 如果止损订单下单失败，开仓和止盈订单已成交
3. **未实现SAGA事务补偿**

---

## 九、字段错误清单

### ❌ 字段名错误
1. **trade_executor.py:257**
   - `"size": existing_position.size`
   - 应该是: `"quantity": existing_position.quantity`

2. **trade_executor.py:384**
   - `order_id=str(order_result['orderId'])`
   - Order模型中没有`order_id`字段，应该是`exchange_order_id`

3. **trade_executor.py:443, 458**
   - `order_id=str(tp_order_result['orderId'])`
   - 同样错误，应该是`exchange_order_id`

4. **trade_executor.py:484**
   - `if instance.enable_step_lock:`
   - Instance模型中字段名是`use_step_locking`，不是`enable_step_lock`

5. **trade_executor.py:492**
   - `step_lock_config=instance.step_lock_config`
   - Instance模型中字段名是`step_config`，不是`step_lock_config`

---

## 十、阻塞问题清单

### 🔴 P0级阻塞（必须修复）

1. **create_stop_market_order函数不存在**
   - 位置: trade_executor.py:428
   - 风险: 止损订单无法下单，系统崩溃
   - 必须: 实现create_stop_market_order或改用create_limit_order

2. **止盈/止损订单未使用clientOrderId**
   - 位置: trade_executor.py:417, 428
   - 风险: 重试会重复下单
   - 必须: 生成并传递clientOrderId

3. **clientOrderId未写入数据库**
   - 位置: trade_executor.py:380-466
   - 风险: 幂等性无法验证
   - 必须: Order对象中设置client_order_id字段

4. **字段名错误**
   - 位置: trade_executor.py:257, 384, 443, 458, 484, 492
   - 风险: KeyError, AttributeError, 系统崩溃
   - 必须: 修正所有字段名

5. **下单成功但DB写入失败无补偿**
   - 位置: trade_executor.py:369-469
   - 风险: 订单泄漏，资金风险
   - 必须: 实现撤单补偿机制

6. **未处理部分成交**
   - 位置: trade_executor.py:389
   - 风险: 持仓数量错误，平仓失败
   - 必须: 查询实际成交数量并更新filled_quantity

7. **无网络重试机制**
   - 位置: trade_executor.py:369
   - 风险: 网络抖动导致订单失败
   - 必须: 实现重试机制，并检查订单是否已存在

8. **无SAGA事务补偿**
   - 位置: trade_executor.py:417-436
   - 风险: 部分订单成功，部分失败，状态不一致
   - 必须: 实现SAGA补偿机制

---

## 十一、最终结论

❌ **交易执行层不可实盘运行**

**原因**:
1. create_stop_market_order函数不存在（P0，系统崩溃）
2. 字段名错误（P0，系统崩溃）
3. clientOrderId未写入数据库（P0，幂等性失效）
4. 止盈/止损订单未使用clientOrderId（P0，重复下单）
5. 下单成功但DB写入失败无补偿（P0，订单泄漏）
6. 未处理部分成交（P0，持仓数量错误）
7. 无网络重试机制（P0，可靠性差）
8. 无SAGA事务补偿（P0，状态不一致）

**必须修复所有P0问题才能进入下一阶段审计。**
