# 第4层审计：状态恢复

## 1. 列出状态机恢复代码

### 状态机定义
**文件**: `core/state_machine.py:30`
```python
RESTARTING = "restarting"  # 重启中
```

**问题**: 
- ❌ 只定义了状态，未找到恢复逻辑
- ❌ 未找到重启时的状态恢复代码

### 搜索恢复相关代码
```bash
grep -rn "recover\|restore\|resume\|restart" backend/
# 结果：只有状态定义，无恢复逻辑
```

---

## 2. 验证真实成交回报恢复路径

### 成交回报处理链路
**文件**: `core/websocket_event_bridge.py:49-109`

#### 链路1: WebSocket → on_order_update
**代码**: 行49-109
```python
async def on_order_update(self, data: Dict[str, Any]):
    order_id = data.get("order_id")
    order_status = data.get("order_status")
    
    # 发布订单更新事件
    await self.event_bus.publish("order.updated", data)
    
    # 如果订单成交
    if order_status == "FILLED":
        # 查询数据库
        order = await db.execute(
            select(Order).where(Order.exchange_order_id == str(order_id))
        )
        
        if order:
            # 更新订单状态
            order.status = "FILLED"
            await db.commit()
            
            # 发布订单成交事件
            await self.event_bus.publish(f"order:filled:{order.id}", {...})
```

**问题**:
1. ✅ 成交回报能更新订单状态
2. ❌ **未更新持仓数量**
3. ❌ **未更新持仓盈亏**
4. ❌ **只更新了订单状态，持仓状态不一致**

#### 链路2: on_position_update
**文件**: `core/websocket_event_bridge.py:111-150`
```python
async def on_position_update(self, data: Dict[str, Any]):
    symbol = data.get("symbol")
    position_amount = data.get("position_amount", 0)
    
    # 发布持仓更新事件
    await self.event_bus.publish("position.updated", data)
    
    # 查询数据库持仓
    position = await db.execute(
        select(Position).where(
            Position.symbol == symbol,
            Position.is_open == True
        )
    )
```

**问题**:
1. ✅ 持仓更新能发布事件
2. ❌ **未更新数据库持仓数量**
3. ❌ **未更新数据库持仓盈亏**
4. ❌ **只发布事件，不更新数据库**

---

## 3. 验证未完成订单恢复逻辑

### 搜索未完成订单查询
```bash
grep -rn "status.*NEW\|status.*PENDING\|status.*PARTIALLY_FILLED" backend/
# 结果：
# - core/order_monitor.py:119 - 查询NEW状态订单
# - plugins/execution_engine/order_executor.py - 定义PENDING状态
```

### 未完成订单处理
**文件**: `core/order_monitor.py:117-121`
```python
result = await self.db.execute(
    select(Order).where(
        Order.position_id == position_id,
        Order.status == "NEW"  # 只查询挂单中的订单
    )
)
```

**问题**:
1. ✅ 能查询NEW状态订单
2. ❌ **未找到重启时恢复未完成订单的代码**
3. ❌ **未找到查询交易所订单状态的代码**
4. ❌ **重启后未完成订单状态不同步**

---

## 4. 验证部分成交恢复

### 搜索部分成交处理
```bash
grep -rn "PARTIALLY_FILLED\|filled_quantity\|partial" backend/
# 结果：
# - core/database.py:189 - 定义filled_quantity字段
# - 无部分成交处理代码
```

### 部分成交字段
**文件**: `core/database.py:189`
```python
filled_quantity = Column(Numeric(20, 8), default=0.0, comment="已成交数量")
```

**问题**:
1. ✅ 数据库有filled_quantity字段
2. ❌ **未找到更新filled_quantity的代码**
3. ❌ **未找到处理部分成交的代码**
4. ❌ **部分成交后持仓数量错误**

---

## 5. 验证重启后不会重复执行信号

### 信号生成逻辑
**文件**: `core/strategy_manager.py:63-93, 151-156`
```python
async def _on_kline_event(self, channel: str, data: dict):
    # 每次K线都会调用策略
    await strategy.on_kline(kline_data)
    
    # 生成信号
    signal = await strategy.generate_signal()
    
    # 发布信号
    await self.event_bus.publish(f"signal:trade:{instance_id}", signal)
```

**问题**:
1. ❌ **每次K线都会生成信号**
2. ❌ **未检查是否已有持仓**
3. ❌ **未检查是否已有挂单**
4. ❌ **重启后收到K线，会重复生成信号**
5. ❌ **可能重复下单**

### 正确做法
```python
async def _on_kline_event(self, channel: str, data: dict):
    # 1. 检查是否已有持仓
    existing_position = await db.query(Position).filter(
        Position.instance_id == instance_id,
        Position.status == "open"
    ).first()
    
    if existing_position:
        # 已有持仓，不生成开仓信号
        return
    
    # 2. 检查是否已有挂单
    existing_order = await db.query(Order).filter(
        Order.instance_id == instance_id,
        Order.status.in_(["NEW", "PENDING"])
    ).first()
    
    if existing_order:
        # 已有挂单，不生成开仓信号
        return
    
    # 3. 生成信号
    signal = await strategy.generate_signal()
```

---

## 6. 若恢复仅依赖验证脚本，标为失败

### 验证脚本
**文件**: `verify_state_recovery.py`
```python
# 这是一个演示脚本，不是真实恢复逻辑
```

**问题**:
1. ❌ verify_state_recovery.py是演示脚本
2. ❌ 不是真实系统的恢复逻辑
3. ❌ **真实系统无恢复逻辑**

---

## 7. P0阻塞清单

### P0-22: 成交回报未更新持仓
**文件**: `websocket_event_bridge.py:74-109`
**问题**: 订单成交后只更新订单状态，未更新持仓数量和盈亏
**影响**: 
- 持仓数量错误
- 持仓盈亏错误
- **资金状态不一致**

### P0-23: 持仓更新未写入数据库
**文件**: `websocket_event_bridge.py:111-150`
**问题**: 持仓更新只发布事件，不更新数据库
**影响**: 
- 数据库持仓状态与交易所不一致
- **重启后持仓状态错误**

### P0-24: 未完成订单无恢复逻辑
**文件**: 全局搜索无结果
**问题**: 重启时未查询交易所订单状态，未恢复未完成订单
**影响**: 
- 重启后未完成订单状态不同步
- **可能遗漏成交**

### P0-25: 部分成交无处理逻辑
**文件**: 全局搜索无结果
**问题**: 未更新filled_quantity，未处理部分成交
**影响**: 
- 部分成交后持仓数量错误
- **资金状态不一致**

### P0-26: 重启后可能重复执行信号
**文件**: `strategy_manager.py:63-93, 151-156`
**问题**: 每次K线都生成信号，未检查已有持仓和挂单
**影响**: 
- 重启后收到K线，会重复生成信号
- **可能重复下单**

### P0-27: 无真实状态恢复逻辑
**文件**: 全局搜索无结果
**问题**: 只有演示脚本，无真实系统的恢复逻辑
**影响**: 
- 重启后状态不恢复
- **系统无法长期运行**

---

## 8. 最终结论

### ❌ 第4层审计失败：状态恢复无法保证

**失败原因**:
1. **成交回报未更新持仓**（只更新订单状态）
2. **持仓更新未写入数据库**（只发布事件）
3. **未完成订单无恢复逻辑**（重启后状态不同步）
4. **部分成交无处理逻辑**（持仓数量错误）
5. **重启后可能重复执行信号**（未检查已有持仓和挂单）
6. **无真实状态恢复逻辑**（只有演示脚本）

**具体文件+行号**:
- websocket_event_bridge.py:74-109 - 成交回报未更新持仓
- websocket_event_bridge.py:111-150 - 持仓更新未写入数据库
- 全局 - 未找到未完成订单恢复逻辑
- 全局 - 未找到部分成交处理逻辑
- strategy_manager.py:63-93, 151-156 - 未检查已有持仓和挂单
- 全局 - 未找到真实状态恢复逻辑

**系统判定**: 
# ❌ 系统不可实盘
# 原因：重启后状态不恢复，持仓和订单状态不一致，可能重复下单，系统无法长期运行
