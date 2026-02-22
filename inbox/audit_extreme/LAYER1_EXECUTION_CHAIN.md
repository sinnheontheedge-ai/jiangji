# 第1层审计：真实执行链唯一性

## 项目文件统计
- **总文件数**: 68个Python文件
- **核心模块**: 28个
- **API模块**: 11个
- **插件模块**: 17个
- **测试模块**: 4个
- **其他**: 8个

---

## 1. 真实信号→执行→下单→DB→EventBus→WebSocket→UI 完整调用链

### 步骤1: 信号生成
**文件**: `core/strategy_manager.py`
**函数**: `_on_kline_event` (行63-93)
**调用链**:
```
strategy_manager._on_kline_event()
  → strategy.on_kline(kline_data)  # 行73
  → signal = strategy.generate_signal()  # 行151
  → event_bus.publish(f"signal:trade:{instance_id}", signal)  # 行153-156
```

**代码位置**:
- 行73: `await strategy.on_kline(kline_data)`
- 行151: `signal = await strategy.generate_signal()`
- 行153-156: `await self.event_bus.publish(...)`

---

### 步骤2: 信号处理 → 下单
**❌ 断链：无人订阅 signal:trade 事件**

**搜索结果**:
```bash
grep -r "signal:trade" backend/
# 发现：
# - strategy_manager.py:153 发布 signal:trade:{instance_id}
# - 无任何文件订阅 signal:trade
```

**问题**:
1. 信号生成后发布到EventBus
2. **无任何模块订阅signal:trade事件**
3. 信号永远不会被处理
4. **执行链断裂**

**预期流程**:
```
trade_executor 应该订阅 signal:trade 事件
  → trade_executor._on_signal(signal)
  → trade_executor._execute_trade(signal)
```

**实际情况**:
- ❌ trade_executor.py 中无任何订阅代码
- ❌ trade_executor.py 中无 _on_signal 方法
- ❌ 信号无法到达执行层

---

### 步骤3: 下单执行
**文件**: `core/trade_executor.py`
**函数**: `_execute_trade` (行421-550)

**调用方式**:
- ❌ **无任何地方调用 _execute_trade**
- ❌ **trade_executor 未启动**
- ❌ **trade_executor 未订阅任何事件**

**搜索结果**:
```bash
grep -r "_execute_trade" backend/
# 只在 trade_executor.py 中定义，无任何调用
```

**问题**:
1. _execute_trade 方法存在
2. 但**无任何地方调用**
3. **下单逻辑永远不会执行**

---

### 步骤4: 数据库写入
**文件**: `core/trade_executor.py`
**函数**: `_execute_trade` (行421-550)

**代码位置**:
- 行505-516: 创建Order对象
- 行518-527: 创建Position对象
- 行529: `await self.db.commit()`

**问题**:
1. 代码存在
2. 但**_execute_trade永远不会被调用**
3. **数据库永远不会写入**

---

### 步骤5: EventBus发布
**❌ trade_executor 未发布任何事件**

**搜索结果**:
```bash
grep -r "event_bus.publish" core/trade_executor.py
# 结果：无匹配
```

**问题**:
1. trade_executor 中无任何 event_bus.publish 调用
2. 下单成功/失败不发布事件
3. 持仓创建/更新不发布事件
4. **EventBus断链**

---

### 步骤6: WebSocket推送
**文件**: `core/websocket_manager.py`
**函数**: `_on_order_created`, `_on_order_filled`, `_on_position_updated` (行62-85)

**订阅事件**:
- 行30: `order.created`
- 行31: `order.filled`
- 行28: `position.updated`

**问题**:
1. websocket_manager 订阅了这些事件
2. 但**trade_executor 不发布这些事件**
3. **WebSocket永远不会推送**

---

### 步骤7: UI更新
**文件**: `frontend/src/pages/Instances.jsx`, `Positions.jsx`, `Orders.jsx`

**WebSocket监听**:
- 前端监听 WebSocket 消息
- 但**后端不推送**
- **UI永远不会更新**

---

## 2. 真实执行链完整性判断

### ❌ 执行链断裂（多处）

**断裂点1**: 信号生成 → 信号处理
- 发布: strategy_manager.py:153
- 订阅: **无**
- **断链**

**断裂点2**: 信号处理 → 下单执行
- 调用: **无任何地方调用 _execute_trade**
- **断链**

**断裂点3**: 下单执行 → EventBus发布
- 发布: **trade_executor 不发布任何事件**
- **断链**

**断裂点4**: EventBus发布 → WebSocket推送
- 订阅: websocket_manager 订阅了 order.created, order.filled, position.updated
- 发布: **trade_executor 不发布这些事件**
- **断链**

**断裂点5**: WebSocket推送 → UI更新
- 推送: **websocket_manager 永远不会推送**
- **断链**

---

## 3. 是否存在 mock/demo/simulate 代码路径

### ✅ 存在Mock路径
**文件**: `core/mock/mock_exchange.py`, `core/mock/mock_binance_client.py`

**问题**:
1. Mock代码存在
2. 但**无法确认是否被使用**
3. 如果被使用，**真实执行链被绕过**

**搜索Mock使用**:
```bash
grep -r "MockExchange\|MockBinanceClient" backend/
# 结果：
# - core/mock/*.py 中定义
# - 无其他文件导入或使用
```

**结论**: Mock代码未被使用，但存在风险

---

### ✅ 存在Demo/Verify脚本
**文件**: 
- `verify_eventbus.py`
- `verify_state_recovery.py`
- `verify_fund_safety.py`
- `verify_step_lock.py`
- `run_e2e_demo.py`

**问题**:
1. 这些是演示脚本
2. **不是真实执行链**
3. 如果误用，**真实执行链被绕过**

---

## 4. 旁路路径风险

### 🔴 风险1: 插件直接导入
**文件**: `main.py:20`, `api/fund_manager.py:16-23`, `api/instances.py:16`

**代码**:
```python
# main.py:20
from plugins.data_source.market_data import MarketDataSource

# api/fund_manager.py:16-23
from plugins.fund_engine.compounding import CompoundingEngine
from plugins.fund_engine.profit_extract import ProfitExtractionEngine
from plugins.fund_engine.auto_replenish import AutoReplenishEngine
```

**问题**:
1. 插件被直接导入
2. **绕过plugin_loader**
3. **插件系统形同虚设**
4. **执行链不唯一**

---

### 🔴 风险2: 多个下单入口
**搜索结果**:
```bash
grep -r "create_market_order\|create_limit_order" backend/
# 发现：
# - binance_client.py 定义
# - trade_executor.py 调用
# - api/positions.py 调用（平仓）
# - plugins/execution_engine/order_executor.py 调用
```

**问题**:
1. 下单函数被多处调用
2. **无统一入口**
3. **执行链不唯一**

---

## 5. 最终结论

### ❌ 第1层审计失败：真实执行链不唯一且断裂

**失败原因**:
1. **信号→执行断链**（无人订阅signal:trade）
2. **执行→下单断链**（_execute_trade永远不被调用）
3. **下单→EventBus断链**（trade_executor不发布事件）
4. **EventBus→WebSocket断链**（无事件发布）
5. **WebSocket→UI断链**（无推送）
6. **存在旁路路径**（插件直接导入，多个下单入口）

**具体文件+行号**:
- strategy_manager.py:153 - 发布signal:trade，但无人订阅
- trade_executor.py:421 - _execute_trade定义，但永远不被调用
- trade_executor.py - 无任何event_bus.publish调用
- websocket_manager.py:28-31 - 订阅事件，但永远不会触发
- main.py:20 - 直接导入插件，绕过plugin_loader
- api/positions.py - 直接调用binance_client下单，绕过trade_executor

**系统判定**: 
# ❌ 系统不可实盘
# 原因：真实执行链完全断裂，信号无法到达下单，下单无法触发EventBus，EventBus无法推送WebSocket，UI无法更新
