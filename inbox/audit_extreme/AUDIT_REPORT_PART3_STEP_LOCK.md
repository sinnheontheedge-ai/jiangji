# 军工级极限审计报告 - 第3部分：Step Lock

## 审计时间
2026-02-21

## 审计范围
- `/tmp/v8_check/v8_docker/backend/core/step_lock_manager.py`
- `/tmp/v8_check/v8_docker/backend/core/step_lock_tick_listener.py`
- `/tmp/v8_check/v8_docker/backend/plugins/risk_engine/tpsl_manager.py`
- `/tmp/v8_check/v8_docker/backend/core/trade_executor.py` (Step Lock集成)
- 所有Step Lock调用链

---

## 一、调用链验证

### 完整调用链
1. **tick数据源** → `strategy_manager.py:169`
   - 发布事件: `risk:step_lock:tick:{symbol}`

2. **tick监听器** → `step_lock_tick_listener.py:23`
   - 订阅事件: `risk:step_lock:tick:*`
   - 调用: `coordinator.check_and_trigger_step_lock()`

3. **Step Lock协调器** → `step_lock_manager.py:102`
   - 查询数据库: `PositionStepLock`
   - 调用: `step_lock_manager.check_level_triggered()`
   - 更新数据库: 档位状态

4. **Step Lock管理器** → `tpsl_manager.py:263`
   - 计算档位触发逻辑
   - 返回新档位和新止损价

5. **事件发布** → `step_lock_tick_listener.py:65`
   - 发布事件: `risk:step_lock:triggered`

6. **WebSocket推送** → `websocket_manager.py:85`
   - 推送到前端: `step_lock_triggered`

### ✅ 调用链完整性
- ✅ tick数据源存在
- ✅ tick监听器存在
- ✅ Step Lock协调器存在
- ✅ Step Lock管理器存在
- ✅ 事件发布存在
- ✅ WebSocket推送存在

### ⚠️ 调用链启动
**文件**: `api/instances.py:210-216`
- ✅ 实例启动时启动Step Lock Tick监听器
- ⚠️ 使用全局单例，只启动一次
- ⚠️ 如果监听器崩溃，无法自动重启

---

## 二、字段映射验证

### ✅ 正确映射
1. **Instance表**
   - ORM字段: `use_step_locking` ✅
   - ORM字段: `step_config` ✅
   - API访问: `instance.use_step_locking` ✅ (instances.py:70, 117, 326)
   - API访问: `instance.step_config` ✅ (instances.py:71, 118, 327)

2. **PositionStepLock表**
   - ORM字段: `position_id`, `current_level`, `peak_price`, `levels_config`, `last_check_time` ✅
   - 协调器访问: 全部正确 ✅

### ❌ 错误映射
**文件**: `trade_executor.py:484`
```python
if instance.enable_step_lock:
```
- ❌ Instance模型中字段名是 `use_step_locking`，不是 `enable_step_lock`
- **会导致AttributeError**

**文件**: `trade_executor.py:492`
```python
step_lock_config=instance.step_lock_config
```
- ❌ Instance模型中字段名是 `step_config`，不是 `step_lock_config`
- **会导致AttributeError**

---

## 三、数学公式验证

### ✅ 公式实现正确
**文件**: `tpsl_manager.py:220-248`

**做多 (LONG)**:
- 触发价格: `threshold_price = entry_price * (1 + threshold_pct / 100)` ✅
- 锁盈价格: `lock_price = entry_price * (1 + lock_pct / 100)` ✅

**做空 (SHORT)**:
- 触发价格: `threshold_price = entry_price * (1 - threshold_pct / 100)` ✅
- 锁盈价格: `lock_price = entry_price * (1 - lock_pct / 100)` ✅

**符合用户需求**:
- ✅ 所有计算基于entry_price
- ✅ 做多用加法 (1 + %)
- ✅ 做空用减法 (1 - %)
- ✅ threshold_pct > lock_pct (由配置保证)

---

## 四、持久化验证

### ✅ 已实现持久化
**文件**: `step_lock_manager.py:72-81`
```python
step_lock_state = PositionStepLock(
    position_id=position_id,
    current_level=0,
    peak_price=entry_price,
    levels_config=levels_json,
    last_check_time=datetime.utcnow()
)
self.db.add(step_lock_state)
await self.db.commit()
```

### ✅ 档位更新持久化
**文件**: `step_lock_manager.py:176-179`
```python
step_lock_state.current_level = new_level
step_lock_state.peak_price = current_price
step_lock_state.last_check_time = datetime.utcnow()
await self.db.commit()
```

### ✅ 峰值价格更新持久化
**文件**: `step_lock_manager.py:197-206`
```python
if current_price > step_lock_state.peak_price:
    step_lock_state.peak_price = current_price
    await self.db.commit()
```

---

## 五、重启恢复验证

### ✅ 已实现重启恢复
**文件**: `step_lock_manager.py:128-158`
```python
# 查询Step Lock状态
stmt = select(PositionStepLock).where(
    PositionStepLock.position_id == position_id
)
result = await self.db.execute(stmt)
step_lock_state = result.scalar_one_or_none()

# 重建档位列表
levels = [
    StepLockLevel(
        level=level_data["level"],
        threshold_pct=level_data["threshold_pct"],
        lock_pct=level_data["lock_pct"],
        threshold_price=level_data["threshold_price"],
        lock_price=level_data["lock_price"]
    )
    for level_data in step_lock_state.levels_config
]
```

### ✅ 测试覆盖
**文件**: `tests/test_step_lock.py:214-280`
- 测试: `test_step_lock_recovery_after_restart`
- 验证: 重启后档位状态恢复正确

---

## 六、档位触发逻辑验证

### ✅ 不允许跳级
**文件**: `tpsl_manager.py:263-310` (check_level_triggered方法)
- 逻辑: 只检查 `current_level + 1` 档位
- 不会跳过中间档位

### ✅ 不允许重复触发
**文件**: `step_lock_manager.py:172-179`
- 只有 `triggered == True` 时才更新档位
- `current_level` 递增，不会重复触发同一档位

### ✅ 测试覆盖
**文件**: `tests/test_step_lock.py:146-211`
- 测试: `test_step_lock_no_skip_levels`
- 验证: 价格直接上涨15%，只触发第一档，不跳级

---

## 七、止损订单更新验证

### ❌ 未实现止损订单更新
**文件**: `step_lock_manager.py:172-195`
- ✅ 档位触发后返回 `new_sl_price`
- ❌ 但**未调用交易所API更新止损订单**
- ❌ 持仓的 `stop_loss` 字段**未更新**
- ❌ 原有止损订单**未撤销**

**问题**:
1. Step Lock触发后，止损价格应该上移
2. 但代码只更新了数据库状态，未更新交易所订单
3. 实际止损订单仍然是旧的价格
4. **止损失效**

**正确流程应该是**:
```python
if triggered:
    # 1. 撤销旧止损订单
    await client.cancel_order(old_sl_order_id)
    
    # 2. 下新止损订单
    new_sl_order = await client.create_stop_market_order(
        symbol=position.symbol,
        side="SELL" if position.side == "LONG" else "BUY",
        quantity=position.quantity,
        stop_price=new_sl_price,
        reduce_only=True
    )
    
    # 3. 更新数据库
    position.stop_loss = new_sl_price
    await db.commit()
```

---

## 八、并发安全验证

### ⚠️ 无并发控制
**文件**: `step_lock_manager.py:102-215`
- ❌ `check_and_trigger_step_lock` 方法无锁
- ❌ 如果同时收到多个tick事件，可能并发调用
- ❌ 可能导致档位重复触发或跳级

**风险**:
1. tick1: 读取 current_level=0
2. tick2: 读取 current_level=0
3. tick1: 触发档位1，写入 current_level=1
4. tick2: 触发档位1，写入 current_level=1
5. **档位重复触发**

**建议**: 使用数据库行锁或分布式锁

---

## 九、阻塞问题清单

### 🔴 P0级阻塞（必须修复）

1. **字段名错误**
   - 位置: trade_executor.py:484, 492
   - 字段: `enable_step_lock` → `use_step_locking`, `step_lock_config` → `step_config`
   - 风险: AttributeError，系统崩溃
   - 必须: 修正字段名

2. **止损订单未更新**
   - 位置: step_lock_manager.py:172-195
   - 风险: Step Lock触发后，止损订单仍是旧价格，止损失效
   - 必须: 实现撤销旧止损订单+下新止损订单

3. **无并发控制**
   - 位置: step_lock_manager.py:102
   - 风险: 档位重复触发或跳级
   - 必须: 添加数据库行锁或分布式锁

### 🟡 P1级问题（建议修复）

1. **监听器崩溃无法自动重启**
   - 位置: api/instances.py:210-216
   - 风险: 如果监听器崩溃，Step Lock失效
   - 建议: 添加健康检查和自动重启机制

2. **峰值价格更新频繁commit**
   - 位置: step_lock_manager.py:197-206
   - 风险: 每个tick都commit，数据库压力大
   - 建议: 批量更新或异步更新

---

## 十、最终结论

❌ **Step Lock不可实盘运行**

**原因**:
1. 字段名错误（P0，系统崩溃）
2. 止损订单未更新（P0，止损失效）
3. 无并发控制（P0，档位重复触发）

**必须修复所有P0问题才能进入下一阶段审计。**
