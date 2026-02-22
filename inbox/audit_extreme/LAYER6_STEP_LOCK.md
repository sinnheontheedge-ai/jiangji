# 第6层审计：Step Lock

## 1. 列出真实调用链

### 调用链路图
```
MarketData (tick) 
  → strategy_manager._on_kline_event (行170)
    → event_bus.publish("risk:step_lock:tick:{symbol}")
      → step_lock_tick_listener._on_tick_event
        → step_lock_coordinator.check_and_trigger_step_lock
          → step_lock_manager.check_level_triggered
            → 更新PositionStepLock表
            → event_bus.publish("risk:step_lock:triggered")
              → websocket_manager._on_step_lock_triggered
                → WebSocket推送到前端
```

### ✅ 真实调用链存在

**文件**: 
- `strategy_manager.py:170` - 发布tick事件
- `step_lock_tick_listener.py` - 订阅tick事件（需要创建）
- `step_lock_manager.py:102-215` - 检查和触发逻辑
- `tpsl_manager.py:263-304` - 档位触发检查
- `websocket_manager.py:85-92` - WebSocket推送

---

## 2. 验证字段映射一致

### 数据库字段
**文件**: `core/database.py:161, 222-236`
```python
# Instance表
use_step_locking = Column(Boolean, default=False, comment="是否使用分档锁盈")

# PositionStepLock表
class PositionStepLock(Base):
    __tablename__ = "position_step_locks"
    position_id = Column(Integer, ForeignKey("positions.id"))
    current_level = Column(Integer, default=0)
    levels_config = Column(JSON)
    peak_price = Column(Numeric(20, 8))
    last_check_time = Column(DateTime)
```

### 代码访问字段
**文件**: `api/instances.py:33, 48, 70, 117, 326`
```python
use_step_locking: bool = False  # ✅ 正确
```

**文件**: `core/trade_executor.py:484`
```python
if instance.enable_step_lock:  # ❌ 错误，应该是use_step_locking
```

### ❌ P0-28: 字段名错误
**文件**: `trade_executor.py:484`
**问题**: 使用`enable_step_lock`，但数据库字段是`use_step_locking`
**影响**: 
- Step Lock初始化永远不会执行
- **Step Lock功能完全失效**

---

## 3. 验证公式：LONG (1+%) / SHORT (1-%)

### Step Lock公式实现
**文件**: `tpsl_manager.py:215-261`

#### 做多公式（✅ 正确）
```python
if side == PositionSide.LONG:
    # 做多
    threshold_price = entry_price * (1 + threshold_pct / 100)  # ✅ 正确
    lock_price = entry_price * (1 + lock_pct / 100)  # ✅ 正确
```

#### 做空公式（✅ 正确）
```python
else:
    # 做空
    threshold_price = entry_price * (1 - threshold_pct / 100)  # ✅ 正确
    lock_price = entry_price * (1 - lock_pct / 100)  # ✅ 正确
```

### ✅ 公式正确

**验证**:
- 做多: `entry_price * (1 + %)` ✅
- 做空: `entry_price * (1 - %)` ✅
- 基于entry_price ✅

---

## 4. 验证基于entry_price

### 公式参数
**文件**: `tpsl_manager.py:215-261`
```python
def calculate_levels(self, entry_price: float, side: PositionSide) -> List[StepLockLevel]:
    """
    Args:
        entry_price: 进场价格 P_entry  # ✅ 基于entry_price
    """
    for i, level_config in enumerate(self.levels_config, start=1):
        threshold_pct = level_config["threshold_pct"]
        lock_pct = level_config["lock_pct"]
        
        if side == PositionSide.LONG:
            threshold_price = entry_price * (1 + threshold_pct / 100)  # ✅ 基于entry_price
            lock_price = entry_price * (1 + lock_pct / 100)  # ✅ 基于entry_price
```

### ✅ 基于entry_price正确

---

## 5. 验证档位持久化

### 持久化代码
**文件**: `step_lock_manager.py:71-81`
```python
# 保存到数据库
step_lock_state = PositionStepLock(
    position_id=position_id,
    current_level=0,  # 初始档位为0
    levels_config=levels_config,  # ✅ 档位配置持久化
    peak_price=entry_price,  # 初始峰值为开仓价
    last_check_time=datetime.utcnow()
)

self.db.add(step_lock_state)
await self.db.commit()  # ✅ 提交到数据库
```

### 档位更新代码
**文件**: `step_lock_manager.py:175-179`
```python
if triggered:
    old_level = step_lock_state.current_level
    
    # 更新状态
    step_lock_state.current_level = new_level  # ✅ 更新档位
    step_lock_state.peak_price = current_price  # ✅ 更新峰值
    step_lock_state.last_check_time = datetime.utcnow()
    await self.db.commit()  # ✅ 提交到数据库
```

### ✅ 档位持久化正确

---

## 6. 验证重启后恢复档位

### 恢复逻辑
**文件**: `step_lock_manager.py:128-138`
```python
# 查询Step Lock状态
stmt = select(PositionStepLock).where(
    PositionStepLock.position_id == position_id
)
result = await self.db.execute(stmt)
step_lock_state = result.scalar_one_or_none()  # ✅ 从数据库读取

if not step_lock_state:
    logger.warning(f"⚠️ 未找到Step Lock状态: position_id={position_id}")
    return None
```

### 档位恢复代码
**文件**: `step_lock_manager.py:148-170`
```python
# 重建档位列表
levels = [
    StepLockLevel(
        level=level_data["level"],
        threshold_pct=level_data["threshold_pct"],
        lock_pct=level_data["lock_pct"],
        threshold_price=level_data["threshold_price"],
        lock_price=level_data["lock_price"]
    )
    for level_data in step_lock_state.levels_config  # ✅ 从数据库恢复
]

# 检查是否触发新档位
triggered, new_level, new_sl_price = step_lock_manager.check_level_triggered(
    current_price=current_price,
    levels=levels,
    current_level=step_lock_state.current_level,  # ✅ 使用数据库中的当前档位
    side=position_side
)
```

### ✅ 重启后恢复档位正确

---

## 7. 验证不跳级、不重复触发

### 档位检查逻辑
**文件**: `tpsl_manager.py:263-304`
```python
def check_level_triggered(
    self,
    current_price: float,
    levels: List[StepLockLevel],
    current_level: int,  # 当前档位
    side: PositionSide
) -> Tuple[bool, int, Optional[float]]:
    for level in levels:
        # 只检查比当前档位更高的档位
        if level.level <= current_level:  # ✅ 防止重复触发
            continue
        
        # 检查触发条件
        triggered = False
        if side == PositionSide.LONG:
            triggered = current_price >= level.threshold_price
        else:
            triggered = current_price <= level.threshold_price
        
        if triggered:
            return True, level.level, level.lock_price  # ✅ 返回第一个触发的档位
    
    return False, current_level, None
```

### ✅ 不跳级、不重复触发正确

**验证**:
1. `level.level <= current_level: continue` - 防止重复触发
2. 返回第一个触发的档位 - 防止跳级
3. 档位递增检查 - 顺序触发

---

## 8. 验证tick级接入

### tick事件发布
**文件**: `strategy_manager.py:167-175`
```python
async def _on_kline_event(self, channel: str, data: dict):
    # 处理K线数据
    ...
    
    # 发布tick事件用于Step Lock检查
    await self.event_bus.publish(
        f"risk:step_lock:tick:{symbol}",
        {
            "symbol": symbol,
            "price": kline_data.get("close"),
            "timestamp": kline_data.get("timestamp")
        }
    )
```

### ❌ P0-29: tick监听器未创建
**文件**: `step_lock_tick_listener.py`
**问题**: 文件不存在，tick事件无人订阅
**影响**: 
- tick事件发布后无人处理
- **Step Lock永远不会触发**

### ❌ P0-30: tick监听器未启动
**文件**: `api/instances.py:211-215`
```python
from core.step_lock_tick_listener import step_lock_tick_listener

if not hasattr(step_lock_tick_listener, '_started'):
    await step_lock_tick_listener.start()
    step_lock_tick_listener._started = True
```
**问题**: 导入的模块不存在
**影响**: 
- 启动实例时会报错
- **系统崩溃**

---

## 9. P0阻塞清单

### P0-28: 字段名错误
**文件**: `trade_executor.py:484`
**问题**: 使用`enable_step_lock`，但数据库字段是`use_step_locking`
**影响**: Step Lock初始化永远不会执行，功能完全失效

### P0-29: tick监听器未创建
**文件**: `step_lock_tick_listener.py`
**问题**: 文件不存在，tick事件无人订阅
**影响**: tick事件发布后无人处理，Step Lock永远不会触发

### P0-30: tick监听器导入错误
**文件**: `api/instances.py:211-215`
**问题**: 导入不存在的模块
**影响**: 启动实例时会报错，系统崩溃

---

## 10. 最终结论

### ❌ 第6层审计失败：Step Lock无法正常工作

**失败原因**:
1. **字段名错误**（enable_step_lock vs use_step_locking）
2. **tick监听器未创建**（step_lock_tick_listener.py不存在）
3. **tick监听器导入错误**（导入不存在的模块）

**成功部分**:
1. ✅ 数学公式正确（LONG 1+%, SHORT 1-%）
2. ✅ 基于entry_price正确
3. ✅ 档位持久化正确
4. ✅ 重启后恢复档位正确
5. ✅ 不跳级、不重复触发正确

**具体文件+行号**:
- trade_executor.py:484 - 字段名错误
- step_lock_tick_listener.py - 文件不存在
- api/instances.py:211-215 - 导入错误

**系统判定**: 
# ❌ 系统不可实盘
# 原因：Step Lock初始化永远不会执行，tick监听器不存在，导入错误会导致系统崩溃
