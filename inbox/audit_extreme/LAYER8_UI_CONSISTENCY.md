# 第8层审计：UI ↔ 后端一致性

## 1. 列出所有前端页面

### 前端页面列表
```
frontend/src/pages/
├── Accounts.jsx          # 账户管理
├── Dashboard.jsx         # 仪表盘
├── FundManager.jsx       # 资金管理
├── Instances.jsx         # 实例管理
├── Notifications.jsx     # 通知管理
├── Orders.jsx            # 订单管理
├── Positions.jsx         # 持仓管理
├── Settings.jsx          # 设置
├── Strategies.jsx        # 策略管理
├── Symbols.jsx           # 交易对管理
├── System.jsx            # 系统管理
└── ThemeSettings.jsx     # 主题设置
```

**总计**: 12个页面

---

## 2. 映射前端按钮到后端API

### 实例管理页面（Instances.jsx）

| 按钮 | 前端调用 | 后端API | 状态 |
|------|---------|---------|------|
| 启动实例 | POST /api/v1/instances/{id}/start | instances.py:88 | ✅ 对应 |
| 停止实例 | POST /api/v1/instances/{id}/stop | instances.py:238 | ✅ 对应 |
| 创建实例 | POST /api/v1/instances | instances.py:56 | ✅ 对应 |
| 编辑实例 | PUT /api/v1/instances/{id} | instances.py:300 | ✅ 对应 |
| 删除实例 | DELETE /api/v1/instances/{id} | instances.py:343 | ✅ 对应 |

**文件**: `Instances.jsx:330, 333, 336`
```jsx
<button onClick={() => handleStatusToggle(instance)}>启动/停止</button>
<button onClick={() => openEditModal(instance)}>编辑</button>
<button onClick={() => handleDelete(instance.id)}>删除</button>
```

**文件**: `Instances.jsx:handleStatusToggle`
```jsx
const handleStatusToggle = async (instance) => {
  if (instance.status === 'running') {
    await axios.post(`/api/v1/instances/${instance.id}/stop`);  // ✅ 正确
  } else {
    await axios.post(`/api/v1/instances/${instance.id}/start`);  // ✅ 正确
  }
};
```

### ✅ 实例管理页面API一致

---

### 资金管理页面（FundManager.jsx）

| 按钮 | 前端调用 | 后端API | 状态 |
|------|---------|---------|------|
| 获取配置 | GET /api/fund-manager/config/{id} | fund_manager.py:184 | ✅ 对应 |
| 保存配置 | PUT /api/fund-manager/config/{id} | ❌ 不存在 | ❌ 空壳 |
| 创建配置 | POST /api/fund-manager/config | fund_manager.py:106 | ✅ 对应 |

**文件**: `FundManager.jsx:86, 156, 159`
```jsx
// 获取配置
const response = await axios.get(`${API_BASE_URL}/api/fund-manager/config/${selectedAccountId}`);

// 保存配置
if (existingConfig) {
  await axios.put(`${API_BASE_URL}/api/fund-manager/config/${selectedAccountId}`, payload);  // ❌ 后端无此路由
} else {
  await axios.post(`${API_BASE_URL}/api/fund-manager/config`, payload);  // ✅ 正确
}
```

**后端路由**:
```bash
grep -n "@router.put.*fund-manager" backend/api/fund_manager.py
# 结果：无匹配
```

### ❌ P0-32: 前端调用不存在的PUT API
**文件**: `FundManager.jsx:156`
**问题**: 前端调用PUT /api/fund-manager/config/{id}，但后端无此路由
**影响**: 
- 更新资金配置时会报错404
- **资金配置无法更新**

---

### 持仓管理页面（Positions.jsx）

| 按钮 | 前端调用 | 后端API | 状态 |
|------|---------|---------|------|
| 平仓 | POST /api/v1/positions/{id}/close | positions.py:104 | ✅ 对应 |
| 查询持仓 | GET /api/v1/positions | positions.py:23 | ✅ 对应 |

### ✅ 持仓管理页面API一致

---

### 订单管理页面（Orders.jsx）

| 按钮 | 前端调用 | 后端API | 状态 |
|------|---------|---------|------|
| 取消订单 | POST /api/v1/orders/{id}/cancel | orders.py:116 | ✅ 对应 |
| 查询订单 | GET /api/v1/orders | orders.py:23 | ✅ 对应 |

### ✅ 订单管理页面API一致

---

## 3. 验证API是否调用核心执行层

### 启动实例API
**文件**: `api/instances.py:88-236`
```python
@router.post("/{instance_id}/start")
async def start_instance(instance_id: int, db: AsyncSession = Depends(get_db)):
    # 1. 查询实例
    instance = await db.get(Instance, instance_id)
    
    # 2. 更新状态
    instance.status = "running"
    await db.commit()
    
    # 3. 启动策略管理器
    strategy_manager = get_strategy_manager()
    await strategy_manager.start_instance(instance_id, instance)
    
    # 4. 启动Step Lock监听器
    from core.step_lock_tick_listener import step_lock_tick_listener
    await step_lock_tick_listener.start()
    
    # 5. 发布事件
    await event_bus.publish("instance.started", {...})
```

### ✅ 启动实例API调用核心执行层
- ✅ 调用strategy_manager.start_instance
- ✅ 启动Step Lock监听器
- ✅ 发布事件

---

### 平仓API
**文件**: `api/positions.py:104-160`
```python
@router.post("/positions/{position_id}/close")
async def close_position(position_id: int, db: AsyncSession = Depends(get_db)):
    # 1. 查询持仓
    position = await db.get(Position, position_id)
    
    # 2. 获取BinanceClient
    client = await get_binance_client(account)
    
    # 3. 下单平仓
    order_result = await client.create_market_order(
        symbol=position.symbol,
        side="sell" if position.side == "LONG" else "buy",
        amount=abs(position.amount),
        reduce_only=True,  # ✅ 强制reduceOnly
        client_order_id=client_order_id  # ✅ 幂等性
    )
    
    # 4. 更新持仓状态
    position.is_open = False
    await db.commit()
    
    # 5. 发布事件
    await event_bus.publish("position.closed", {...})
```

### ✅ 平仓API调用核心执行层
- ✅ 调用binance_client.create_market_order
- ✅ 强制reduceOnly=True
- ✅ 使用clientOrderId幂等性
- ✅ 发布事件

---

## 4. 验证不存在空壳API

### 搜索空壳API
```bash
# 搜索只返回固定值的API
grep -A 10 "@router\." backend/api/*.py | grep "return {" | head -20
```

### 示例：空壳API
**文件**: `api/notifications.py:30-50`
```python
@router.get("/system/notifications/config")
async def get_notification_config():
    # 返回固定配置
    return {
        "telegram_enabled": False,
        "email_enabled": False,
        ...
    }
```

**问题**:
- ⚠️ 返回固定值，未从数据库读取
- ⚠️ 可能是空壳API

### ⚠️ 警告：存在空壳API
**影响**: 部分API可能未真实实现，但不影响核心交易功能

---

## 5. 验证WebSocket推送来源真实DB

### WebSocket推送逻辑
**文件**: `core/websocket_manager.py:20-92`
```python
async def start(self):
    # 订阅EventBus事件
    await self.event_bus.subscribe("order.created", self._on_order_created)
    await self.event_bus.subscribe("order.filled", self._on_order_filled)
    await self.event_bus.subscribe("position.opened", self._on_position_opened)
    await self.event_bus.subscribe("position.closed", self._on_position_closed)
    await self.event_bus.subscribe("risk:step_lock:triggered", self._on_step_lock_triggered)
    ...

async def _on_order_created(self, channel: str, event_data: Dict[str, Any]):
    # 推送到前端
    await self.broadcast({
        'type': 'order_created',
        'data': event_data
    })
```

### WebSocket推送来源
**来源1**: 订单创建事件
- **发布者**: `trade_executor.py` (但_execute_trade永远不被调用)
- **问题**: ❌ 事件永远不会发布

**来源2**: 订单成交事件
- **发布者**: `websocket_event_bridge.py:on_user_data_event`
- **触发**: Binance WebSocket成交回报
- **状态**: ✅ 真实来源

**来源3**: 持仓开仓事件
- **发布者**: `trade_executor.py` (但_execute_trade永远不被调用)
- **问题**: ❌ 事件永远不会发布

**来源4**: 持仓平仓事件
- **发布者**: `api/positions.py:close_position`
- **状态**: ✅ 真实来源

**来源5**: Step Lock触发事件
- **发布者**: `step_lock_manager.py` (但tick监听器不存在)
- **问题**: ❌ 事件永远不会发布

### ⚠️ 部分WebSocket推送来源真实DB，部分断链
**问题**:
- ✅ 订单成交事件来源真实（Binance WebSocket）
- ✅ 持仓平仓事件来源真实（API调用）
- ❌ 订单创建事件断链（trade_executor不被调用）
- ❌ 持仓开仓事件断链（trade_executor不被调用）
- ❌ Step Lock触发事件断链（tick监听器不存在）

---

## 6. P0阻塞清单

### P0-32: 前端调用不存在的PUT API
**文件**: `FundManager.jsx:156`
**问题**: 前端调用PUT /api/fund-manager/config/{id}，但后端无此路由
**影响**: 更新资金配置时会报错404，资金配置无法更新

---

## 7. 最终结论

### ⚠️ 第8层审计部分通过：UI↔后端大部分一致，但存在问题

**成功部分**:
1. ✅ 实例管理页面API一致
2. ✅ 持仓管理页面API一致
3. ✅ 订单管理页面API一致
4. ✅ 启动实例API调用核心执行层
5. ✅ 平仓API调用核心执行层
6. ✅ 部分WebSocket推送来源真实DB

**问题部分**:
1. ❌ 资金管理页面PUT API不存在（P0-32）
2. ⚠️ 存在空壳API（不影响核心功能）
3. ❌ 部分WebSocket推送断链（订单创建/持仓开仓/Step Lock触发）

**具体文件+行号**:
- FundManager.jsx:156 - 调用不存在的PUT API
- trade_executor.py - 不发布订单创建/持仓开仓事件
- step_lock_tick_listener.py - 文件不存在，Step Lock触发事件断链

**系统判定**: 
# ⚠️ UI↔后端大部分一致，但存在P0阻塞
# 原因：资金配置无法更新，部分WebSocket推送断链
