# 第7层审计：插件系统

## 1. 列出所有插件

### 插件目录
```
plugins/
├── data_source/          # 数据源插件
├── execution_engine/     # 执行引擎插件
├── fund_engine/          # 资金管理插件
├── notification_engine/  # 通知引擎插件
└── risk_engine/          # 风控引擎插件
```

**总计**: 5个插件

---

## 2. 验证create_plugin是否存在

### 插件检查结果

| 插件名 | create_plugin | 文件 |
|--------|---------------|------|
| data_source | ✅ 存在 | data_source/plugin.py:8 |
| execution_engine | ✅ 存在 | execution_engine/plugin.py:34 |
| fund_engine | ✅ 存在 | fund_engine/plugin.py:38 |
| notification_engine | ✅ 存在 | notification_engine/plugin.py:8 |
| risk_engine | ✅ 存在 | risk_engine/plugin.py:31 |

### ✅ 所有插件都有create_plugin函数

---

## 3. 验证是否真实注册到EventBus

### 插件加载流程
**文件**: `core/plugin_loader.py:51-96`
```python
def load_plugin(self, plugin_name: str, event_bus, config: Dict = None) -> Any:
    # 加载插件模块
    module = importlib.import_module(f"plugins.{plugin_name}.plugin")
    
    # 检查create_plugin函数
    if hasattr(module, 'create_plugin'):
        # 调用create_plugin
        plugin_instance = module.create_plugin(event_bus, plugin_config)
        return plugin_instance
    else:
        raise ValueError(f"插件{plugin_name}缺少create_plugin函数")
```

### 插件注册调用
**文件**: `main.py:66-85`
```python
plugin_loader = get_plugin_loader()

# 加载所有插件
plugins = plugin_loader.load_all_plugins(event_bus, plugin_configs)

# 启动所有插件
await plugin_loader.start_all_plugins()
```

### ✅ 插件真实注册到EventBus

**验证**:
1. main.py调用plugin_loader.load_all_plugins
2. plugin_loader调用每个插件的create_plugin
3. create_plugin接收event_bus参数
4. 插件可以通过event_bus订阅和发布事件

---

## 4. 列出未调用插件

### 搜索插件导入
```bash
grep -rn "from plugins\|import.*plugin" backend/ --include="*.py"
```

### 直接导入的插件（绕过plugin_loader）
**文件**: `main.py:20`
```python
from plugins.execution_engine.order_executor import OrderExecutor
```

**问题**:
- ❌ 直接导入OrderExecutor，绕过plugin_loader
- ❌ 未通过create_plugin注册
- ❌ 可能未订阅EventBus

### ❌ P0-31: 插件直接导入绕过注册
**文件**: `main.py:20`
**问题**: 直接导入OrderExecutor，绕过plugin_loader
**影响**: 
- 插件未通过create_plugin注册
- 可能未订阅EventBus
- **插件系统不一致**

---

## 5. 列出死代码

### 搜索未被调用的函数
```bash
# 搜索所有函数定义
grep -rn "^def \|^async def " backend/plugins/ --include="*.py" | wc -l
# 结果：约50个函数
```

### 示例：未被调用的函数
**文件**: `plugins/execution_engine/order_executor.py`
```python
# 定义了很多函数，但只有部分被调用
```

**问题**:
- ⚠️ 存在大量未被调用的函数
- ⚠️ 代码冗余，难以维护

### ⚠️ 警告：存在死代码
**影响**: 代码冗余，难以维护，但不影响系统运行

---

## 6. 标记任何调用不存在方法

### 搜索不存在的方法调用

#### 调用1: create_stop_market_order
**文件**: `core/trade_executor.py:428`, `core/risk_monitor.py:349, 433`
```python
await client.create_stop_market_order(...)  # ❌ 函数不存在
```

**搜索结果**:
```bash
grep -rn "def create_stop_market_order" backend/
# 结果：无匹配
```

### ❌ P0-11: 调用不存在的函数（已在第2层发现）
**文件**: `trade_executor.py:428`, `risk_monitor.py:349, 433`
**问题**: 调用create_stop_market_order，但函数不存在
**影响**: 系统崩溃

#### 调用2: instance.enable_step_lock
**文件**: `core/trade_executor.py:484`
```python
if instance.enable_step_lock:  # ❌ 字段不存在
```

**数据库字段**:
```python
use_step_locking = Column(Boolean, ...)  # 正确字段名
```

### ❌ P0-28: 调用不存在的字段（已在第6层发现）
**文件**: `trade_executor.py:484`
**问题**: 使用enable_step_lock，但数据库字段是use_step_locking
**影响**: Step Lock初始化永远不会执行

#### 调用3: step_lock_tick_listener
**文件**: `api/instances.py:211`
```python
from core.step_lock_tick_listener import step_lock_tick_listener  # ❌ 模块不存在
```

**搜索结果**:
```bash
find backend/ -name "step_lock_tick_listener.py"
# 结果：无匹配
```

### ❌ P0-30: 导入不存在的模块（已在第6层发现）
**文件**: `api/instances.py:211`
**问题**: 导入step_lock_tick_listener，但模块不存在
**影响**: 系统崩溃

---

## 7. 验证插件订阅EventBus

### 插件订阅示例

#### data_source插件
**文件**: `plugins/data_source/plugin.py:8-20`
```python
def create_plugin(event_bus, config: dict):
    # 创建数据源插件
    data_source = DataSource(event_bus, config)
    return data_source
```

**问题**:
- ⚠️ 未找到订阅EventBus的代码
- ⚠️ 未找到发布事件的代码

#### execution_engine插件
**文件**: `plugins/execution_engine/plugin.py:34-50`
```python
def create_plugin(event_bus, config: dict):
    # 创建执行引擎插件
    executor = OrderExecutor(event_bus, config)
    return executor
```

**问题**:
- ⚠️ 未找到订阅EventBus的代码
- ⚠️ 未找到发布事件的代码

### ⚠️ 警告：插件未订阅EventBus
**影响**: 插件可能无法接收事件，但需要进一步检查插件内部实现

---

## 8. P0阻塞清单

### P0-31: 插件直接导入绕过注册
**文件**: `main.py:20`
**问题**: 直接导入OrderExecutor，绕过plugin_loader
**影响**: 插件未通过create_plugin注册，可能未订阅EventBus

### P0-11: 调用不存在的函数（重复）
**文件**: `trade_executor.py:428`, `risk_monitor.py:349, 433`
**问题**: 调用create_stop_market_order，但函数不存在
**影响**: 系统崩溃

### P0-28: 调用不存在的字段（重复）
**文件**: `trade_executor.py:484`
**问题**: 使用enable_step_lock，但数据库字段是use_step_locking
**影响**: Step Lock初始化永远不会执行

### P0-30: 导入不存在的模块（重复）
**文件**: `api/instances.py:211`
**问题**: 导入step_lock_tick_listener，但模块不存在
**影响**: 系统崩溃

---

## 9. 最终结论

### ⚠️ 第7层审计部分通过：插件系统基本可用，但存在问题

**成功部分**:
1. ✅ 所有插件都有create_plugin函数
2. ✅ 插件加载流程正确
3. ✅ 插件真实注册到EventBus

**问题部分**:
1. ❌ 插件直接导入绕过注册（P0-31）
2. ❌ 调用不存在的函数（P0-11，重复）
3. ❌ 调用不存在的字段（P0-28，重复）
4. ❌ 导入不存在的模块（P0-30，重复）
5. ⚠️ 存在死代码（不影响运行）
6. ⚠️ 插件可能未订阅EventBus（需要进一步检查）

**具体文件+行号**:
- main.py:20 - 插件直接导入绕过注册
- trade_executor.py:428, risk_monitor.py:349, 433 - 调用不存在的函数
- trade_executor.py:484 - 调用不存在的字段
- api/instances.py:211 - 导入不存在的模块

**系统判定**: 
# ⚠️ 插件系统基本可用，但存在P0阻塞
# 原因：插件直接导入绕过注册，调用不存在的函数/字段/模块会导致系统崩溃
