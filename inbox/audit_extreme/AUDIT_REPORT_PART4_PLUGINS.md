# 军工级极限审计报告 - 第4部分：插件系统

## 审计时间
2026-02-21

## 审计范围
- `/tmp/v8_check/v8_docker/backend/core/plugin_loader.py`
- `/tmp/v8_check/v8_docker/backend/plugins/*/plugin.py`
- 所有插件注册和调用

---

## 一、插件清单

### 已发现插件（5个）
1. **data_source** - 数据源插件
   - ✅ plugin.json 存在
   - ✅ plugin.py 存在
   - ✅ create_plugin 函数存在

2. **execution_engine** - 执行引擎插件
   - ✅ plugin.json 存在
   - ✅ plugin.py 存在
   - ✅ create_plugin 函数存在

3. **fund_engine** - 资金引擎插件
   - ✅ plugin.json 存在
   - ✅ plugin.py 存在
   - ✅ create_plugin 函数存在

4. **notification_engine** - 通知引擎插件
   - ✅ plugin.json 存在
   - ✅ plugin.py 存在
   - ✅ create_plugin 函数存在

5. **risk_engine** - 风控引擎插件
   - ✅ plugin.json 存在
   - ✅ plugin.py 存在
   - ✅ create_plugin 函数存在

---

## 二、create_plugin函数验证

### ✅ 所有插件都有create_plugin函数
- ✅ data_source/plugin.py:8
- ✅ execution_engine/plugin.py:34
- ✅ fund_engine/plugin.py:38
- ✅ notification_engine/plugin.py:8
- ✅ risk_engine/plugin.py:31

---

## 三、插件注册验证

### ✅ 插件加载机制存在
**文件**: `core/plugin_loader.py`
- ✅ PluginLoader类实现完整
- ✅ discover_plugins方法：发现所有插件
- ✅ load_plugin方法：加载单个插件
- ✅ load_all_plugins方法：加载所有插件
- ✅ start_all_plugins方法：启动所有插件
- ✅ stop_all_plugins方法：停止所有插件

### ✅ 插件在main.py中加载
**文件**: `main.py:81`
```python
plugins = plugin_loader.load_all_plugins(event_bus, plugin_configs)
```

### ❌ 插件未启动
**文件**: `main.py`
- ✅ 第81行：加载插件
- ❌ **未调用 `plugin_loader.start_all_plugins()`**
- ❌ 插件加载后未启动，插件功能不生效

---

## 四、插件直接导入验证

### ❌ 插件被直接导入，绕过插件系统
**文件**: `main.py:20`
```python
from plugins.data_source.market_data import MarketDataSource
```
- ❌ 直接导入MarketDataSource，绕过plugin_loader
- ❌ 插件系统失去意义

**文件**: `api/fund_manager.py:16-23`
```python
from plugins.fund_engine.compounding import CompoundingEngine, CompoundingMode
from plugins.fund_engine.profit_extract import ProfitExtractionEngine, ...
from plugins.fund_engine.auto_replenish import AutoReplenishEngine
```
- ❌ 直接导入资金引擎类，绕过plugin_loader

**文件**: `api/instances.py:16`
```python
from plugins.data_source.market_data import MarketDataSource
```
- ❌ 直接导入MarketDataSource

**文件**: `core/fund_monitor.py:13-14`
```python
from plugins.fund_engine.profit_extract import ProfitExtractionEngine
from plugins.fund_engine.auto_replenish import AutoReplenishEngine
```
- ❌ 直接导入资金引擎类

**文件**: `core/websocket_event_bridge.py:168`
```python
from plugins.risk_engine.tpsl_manager import TPSLManager
```
- ❌ 直接导入TPSLManager

**文件**: `core/step_lock_manager.py:11`
```python
from plugins.risk_engine.tpsl_manager import StepLockManager, StepLockLevel, PositionSide
```
- ❌ 直接导入Step Lock相关类

**问题**:
1. 插件系统加载的插件实例未被使用
2. 业务代码直接导入插件类，创建新实例
3. 插件系统形同虚设
4. 插件配置不生效
5. 插件生命周期管理失效

---

## 五、插件EventBus订阅验证

### ❌ 无法验证插件是否订阅EventBus
**原因**:
1. 插件未启动（未调用start_all_plugins）
2. 插件被直接导入，不是通过plugin_loader获取
3. 无法确认插件是否真实注册到主EventBus

**需要验证**:
- data_source插件是否订阅了行情事件？
- execution_engine插件是否订阅了交易信号？
- fund_engine插件是否订阅了资金事件？
- notification_engine插件是否订阅了通知事件？
- risk_engine插件是否订阅了风控事件？

---

## 六、死代码验证

### ❌ 插件系统是死代码
**文件**: `core/plugin_loader.py`
- 整个PluginLoader类实现完整
- 但**插件未启动**
- **插件被直接导入**
- **插件系统未被真正使用**

### ❌ 插件配置未生效
**文件**: `main.py:62-78`
```python
plugin_configs = {
    "data_source": {"enabled": True},
    "execution_engine": {"enabled": True},
    "fund_engine": {"enabled": True},
    "notification_engine": {"enabled": True},
    "risk_engine": {"enabled": True}
}
```
- 配置定义了，但**插件未启动**
- 配置不生效

---

## 七、不存在方法调用验证

### ❌ 调用了不存在的方法
**文件**: `core/websocket_event_bridge.py:168-170`
```python
from plugins.risk_engine.tpsl_manager import TPSLManager
tpsl_manager = TPSLManager(db, None)  # client会在需要时传入
await tpsl_manager.update_stop_loss(...)
```

**问题**:
1. 查看TPSLManager类定义（tpsl_manager.py）
2. **未找到update_stop_loss方法**
3. 调用会导致AttributeError

---

## 八、阻塞问题清单

### 🔴 P0级阻塞（必须修复）

1. **插件未启动**
   - 位置: main.py
   - 风险: 插件加载后未启动，插件功能不生效
   - 必须: 调用 `await plugin_loader.start_all_plugins()`

2. **插件被直接导入，绕过插件系统**
   - 位置: main.py:20, api/fund_manager.py:16-23, api/instances.py:16, core/fund_monitor.py:13-14, core/websocket_event_bridge.py:168, core/step_lock_manager.py:11
   - 风险: 插件系统形同虚设，配置不生效，生命周期管理失效
   - 必须: 通过plugin_loader.get_plugin()获取插件实例

3. **调用不存在的方法**
   - 位置: core/websocket_event_bridge.py:170
   - 方法: `tpsl_manager.update_stop_loss(...)`
   - 风险: AttributeError，系统崩溃
   - 必须: 实现update_stop_loss方法或删除调用

4. **插件配置未生效**
   - 位置: main.py:62-78
   - 风险: 插件配置定义了但不生效
   - 必须: 确保插件通过plugin_loader加载和启动

### 🟡 P1级问题（建议修复）

1. **插件系统架构混乱**
   - 问题: 既有插件系统，又直接导入插件
   - 建议: 统一使用插件系统或删除插件系统

---

## 九、最终结论

❌ **插件系统不可实盘运行**

**原因**:
1. 插件未启动（P0）
2. 插件被直接导入，绕过插件系统（P0）
3. 调用不存在的方法（P0，系统崩溃）
4. 插件配置未生效（P0）

**必须修复所有P0问题才能进入下一阶段审计。**
