ENGINE_SPEC v1.0

单人量化交易引擎最终规格与验收标准

一、系统目标

本系统的目标是构建一个 稳定、轻量、可长期运行的单人交易引擎。

系统必须满足：

单进程运行

WebSocket 驱动（ON TICK）

实时风控

实时资金管理

本地 GUI 调参

支持多策略

支持多交易对

支持多周期

支持企业微信信号通知

系统不是：

Web 平台

SaaS 系统

多用户系统

二、必须删除的架构

以下架构必须移除或禁用：

Web UI

REST API（交易主链路）

前端项目

EventBus

Plugin Loader

微服务

SaaS 逻辑

内部 WebSocket 推送

系统必须是 单引擎直连架构。

三、系统架构

核心结构必须为：

Binance WebSocket
        ↓
Strategy Engine
        ↓
Risk Control
        ↓
Fund Manager
        ↓
Execution Engine
        ↓
State Store

禁止通过 EventBus 调用。

必须是同步调用链。

四、ON TICK 架构

以下逻辑必须由 WebSocket 触发：

策略触发

进场判断

Step Lock

TP

SL

资金管理

仓位更新

禁止：

轮询交易所

定时任务触发交易

允许：

配置文件热加载检查

五、交易对管理

系统必须支持交易对池：

用户可以：

全选交易对

添加交易对

删除交易对

同步交易所交易对

交易所下线交易对必须自动移除。

配置变更必须支持热加载。

六、K线周期

系统必须支持以下周期：

1m
3m
5m
15m
30m
1h
2h
4h
6h
8h
12h
1d
3d
1w

必须支持多周期同时运行。

K线必须通过 WebSocket 数据生成。

七、策略系统

系统必须提供 策略库。

支持：

添加策略

删除策略

启用策略

禁用策略

修改参数

策略应用方式：

(symbol, timeframe, strategy)

禁止自动笛卡尔组合。

八、策略 Warmup

系统必须实现：

Adaptive Warmup + Readiness Gate

规则：

禁止固定历史数量。

禁止策略声明固定长度。

系统必须按需回补历史数据。

未 READY 前禁止交易。

READY 条件：

所有指标可计算

无 NaN

无窗口不足

系统必须支持逐步扩大历史窗口。

九、风控系统

系统必须支持：

TP

SL

Step Lock

Step Lock 数学公式：

LONG

current_price >= entry_price * (1 + profit_threshold/100)
SL = entry_price * (1 + stop_loss_percent/100)

SHORT

current_price <= entry_price * (1 - profit_threshold/100)
SL = entry_price * (1 - stop_loss_percent/100)

要求：

ON TICK 触发

状态持久化

重启恢复

禁止重复触发

十、订单管理规则

Step Lock 触发后必须：

撤销旧 SL
挂出新 SL

系统任意时刻只能存在：

1 个 SL

当 TP 或 SL 平仓后必须：

撤销剩余 TP
撤销剩余 SL

防止反向开仓。

十一、执行安全

必须满足：

reduceOnly 强制

clientOrderId 幂等

精度校验

部分成交处理

异常补偿

禁止重复下单。

十二、资金管理

资金管理必须 ON TICK。

必须支持：

杠杆降级

保证金计算

自动补保证金

盈利提取

单仓模式

金额计算必须使用：

Decimal
十三、数据库

数据库使用：

SQLite

用途：

订单记录

仓位

状态恢复

资金记录

禁止每 tick 写数据库。

十四、本地 GUI

系统必须提供本地 GUI。

用途：

交易对选择

周期选择

策略管理

风控参数

资金参数

企业微信通知开关

GUI 不参与交易逻辑。

十五、企业微信通知

系统必须支持企业微信机器人。

通知事件：

进场信号

触发时机：

策略确认信号
↓
风控通过
↓
准备下单

通知内容：

交易对

方向

策略

周期

信号价格

止损价格

时间

通知失败不能影响交易。

GUI 必须提供开关。

十六、运行要求

系统必须支持：

python engine_main.py

启动后必须：

成功连接 Binance

收到行情

正常运行

十七、阶段验收标准

第一阶段：

引擎可启动

WS连接成功

收到 tick

第二阶段：

策略触发

风控运行

第三阶段：

GUI 可配置

十八、最终验收

系统必须满足：

可长期运行

自动重连

重启恢复

无重复下单

无仓位翻倍

风控实时

资金管理实时

企业微信通知正常

否则视为未完成。