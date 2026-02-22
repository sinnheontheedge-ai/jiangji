# 军工级极限审计报告 - 第5部分：EventBus

## 审计时间
2026-02-21

## 审计范围
- `/tmp/v8_check/v8_docker/backend/core/event_bus.py`
- 所有publish调用（24处）
- 所有subscribe调用（17处）

---

## 一、EventBus实现验证

### ✅ EventBus基于Redis
**文件**: `event_bus.py:38-42`
```python
self.redis_client = await aioredis.from_url(
    redis_url,
    encoding="utf-8",
    decode_responses=True
)
```
- ✅ 使用Redis作为消息中间件
- ✅ 支持分布式部署
- ✅ 消息持久化（Redis持久化）

### ✅ publish/subscribe实现完整
- ✅ publish方法：发布事件到Redis
- ✅ subscribe方法：订阅Redis频道
- ✅ _listen方法：后台监听Redis消息

---

## 二、commit后publish验证

### ❌ 大量publish在commit之前
**问题**: 如果publish后commit失败，事件已发布但数据库未提交，导致状态不一致。

#### 案例1: trade_executor.py
**文件**: `trade_executor.py` (未找到publish调用)
- ❌ 未找到trade_executor中的publish调用
- ❌ 下单成功后未发布事件
- ❌ EventBus断链

#### 案例2: websocket_event_bridge.py
**文件**: `websocket_event_bridge.py:44, 71, 89, 132, 176, 203`
- ❌ 所有publish都在WebSocket回调中
- ❌ 无法确认是否在commit之后
- ❌ 可能存在publish后commit失败的风险

#### 案例3: fund_monitor.py
**文件**: `fund_monitor.py:318, 357, 402, 467, 517`
- ❌ 所有publish都在资金操作后
- ❌ 无法确认是否在commit之后
- ❌ 可能存在publish后commit失败的风险

### ✅ 正确的顺序应该是
```python
# 1. 数据库操作
order = Order(...)
db.add(order)

# 2. commit
await db.commit()

# 3. publish（commit成功后才发布）
await event_bus.publish("order.created", {...})
```

---

## 三、事件循环验证

### ⚠️ 可能存在事件循环
**文件**: `strategy_manager.py:153`
```python
await self.event_bus.publish(
    f"signal:trade:{instance_id}",
    {...}
)
```

**文件**: `websocket_event_bridge.py:89`
```python
await self.event_bus.publish(
    f"order:filled:{order.id}",
    {...}
)
```

**问题**: 
1. signal:trade事件 → 触发下单 → order:filled事件 → 触发持仓更新 → position.updated事件
2. 如果某个环节错误地订阅了自己发布的事件，会导致无限循环
3. 当前代码未发现明显的循环，但**缺乏防护机制**

### ❌ 无事件循环检测机制
- ❌ 无事件ID或追踪机制
- ❌ 无事件深度限制
- ❌ 无循环检测

---

## 四、事件订阅验证

### ✅ 核心订阅存在
1. **strategy_manager** 订阅:
   - ✅ market_data:kline:*
   - ✅ market_data:tick:*

2. **websocket_manager** 订阅:
   - ✅ position.updated
   - ✅ order.updated
   - ✅ order.created
   - ✅ order.filled
   - ✅ notification.frontend
   - ✅ step_lock.triggered
   - ✅ risk:step_lock:triggered
   - ✅ account.balance_updated
   - ✅ trade:rejected
   - ✅ instance.status_changed

3. **order_monitor** 订阅:
   - ✅ order:filled:*
   - ✅ position:closed:*

4. **step_lock_tick_listener** 订阅:
   - ✅ risk:step_lock:tick:*

5. **notifier** 订阅:
   - ✅ signal.generated

### ❌ 缺少关键订阅
1. **trade_executor** 未订阅signal:trade事件
   - ❌ 信号生成后无人处理
   - ❌ 交易信号断链

2. **fund_monitor** 未订阅任何事件
   - ❌ 资金监控未集成到EventBus
   - ❌ 资金事件断链

---

## 五、事件发布验证

### ✅ 核心事件发布存在
1. **market_data** 发布:
   - ✅ market_data:kline:{symbol}:{interval}
   - ✅ market_data:tick:{symbol}
   - ✅ price:update

2. **strategy_manager** 发布:
   - ✅ signal:trade:{instance_id}
   - ✅ strategy:error:{instance_id}
   - ✅ risk:step_lock:tick:{symbol}

3. **websocket_event_bridge** 发布:
   - ✅ account.balance_updated
   - ✅ order.updated
   - ✅ order:filled:{order.id}
   - ✅ position.updated
   - ✅ step_lock.triggered
   - ✅ position:closed:{position.id}

4. **fund_monitor** 发布:
   - ✅ fund:profit_extracted:{account_id}
   - ✅ fund:auto_replenished:{account_id}
   - ✅ fund:initial_protected:{account_id}
   - ✅ fund:profit_endpoint_reached:{account_id}

5. **step_lock_tick_listener** 发布:
   - ✅ risk:step_lock:triggered

6. **order_executor** 发布:
   - ✅ order:submitted:{account_id}
   - ✅ order:filled:{account_id}

7. **notifier** 发布:
   - ✅ notification.frontend

### ❌ 缺少关键事件发布
1. **trade_executor** 未发布任何事件
   - ❌ 下单成功/失败未发布事件
   - ❌ 持仓创建/更新未发布事件
   - ❌ EventBus断链

2. **order.created** 事件未找到发布者
   - ⚠️ websocket_manager订阅了order.created
   - ❌ 但未找到任何地方发布order.created
   - ❌ 订阅了一个永远不会触发的事件

---

## 六、WebSocket重连验证

### ❌ WebSocket无重连机制
**文件**: `event_bus.py:94-129`
- ✅ _listen方法有异常捕获
- ✅ 异常后等待1秒重试
- ❌ 但**Redis连接断开后未重连**
- ❌ 如果Redis断开，EventBus失效

**问题**:
1. Redis连接断开 → _listen异常 → 等待1秒 → 继续_listen
2. 但**redis_client和pubsub未重新创建**
3. 后续所有publish/subscribe都会失败
4. **EventBus永久失效**

**正确流程应该是**:
```python
async def _listen(self):
    while self.running:
        try:
            if not self.redis_client or not self.redis_client.ping():
                # 重连Redis
                await self._reconnect()
            
            message = await self.pubsub.get_message(...)
            ...
        except Exception as e:
            logger.error(f"事件监听异常: {e}")
            await self._reconnect()  # 重连
            await asyncio.sleep(1)
```

---

## 七、阻塞问题清单

### 🔴 P0级阻塞（必须修复）

1. **trade_executor未发布事件**
   - 位置: trade_executor.py
   - 风险: 下单成功/失败、持仓创建/更新未发布事件，EventBus断链
   - 必须: 在commit后发布order.created, order.filled, position.created, position.updated事件

2. **trade_executor未订阅signal:trade事件**
   - 位置: trade_executor.py
   - 风险: 信号生成后无人处理，交易信号断链
   - 必须: 订阅signal:trade事件并处理

3. **order.created事件无发布者**
   - 位置: 全局搜索
   - 风险: websocket_manager订阅了order.created，但永远不会触发
   - 必须: 在下单成功后发布order.created事件

4. **Redis断开后无重连机制**
   - 位置: event_bus.py:94-129
   - 风险: Redis断开后EventBus永久失效
   - 必须: 实现Redis重连机制

5. **publish在commit之前**
   - 位置: websocket_event_bridge.py, fund_monitor.py
   - 风险: publish后commit失败，事件已发布但数据库未提交，状态不一致
   - 必须: 确保所有publish都在commit之后

### 🟡 P1级问题（建议修复）

1. **无事件循环检测机制**
   - 位置: event_bus.py
   - 风险: 如果某个环节错误地订阅了自己发布的事件，会导致无限循环
   - 建议: 添加事件ID、追踪机制、深度限制

2. **fund_monitor未集成到EventBus**
   - 位置: fund_monitor.py
   - 风险: 资金监控未订阅任何事件，无法响应实时变化
   - 建议: 订阅position.updated, order.filled等事件

---

## 八、最终结论

❌ **EventBus不可实盘运行**

**原因**:
1. trade_executor未发布事件（P0，EventBus断链）
2. trade_executor未订阅signal:trade事件（P0，交易信号断链）
3. order.created事件无发布者（P0）
4. Redis断开后无重连机制（P0，EventBus永久失效）
5. publish在commit之前（P0，状态不一致）

**必须修复所有P0问题才能进入下一阶段审计。**
