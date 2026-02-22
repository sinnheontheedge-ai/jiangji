# 第3层审计：精度安全

## 1. 全局搜索float

### float使用统计
**搜索命令**:
```bash
grep -rn "\bfloat\b" backend/ --include="*.py" | wc -l
# 结果：200+处
```

### float使用分类

#### ✅ 类型注解（无风险）
**文件**: `api/accounts.py:44`, `api/fund_manager.py:35-74`, `api/instances.py:30-46`
```python
balance: float  # 类型注解，不参与计算
```
**数量**: 约50处
**风险**: 无

#### ❌ 类型转换（高风险）
**文件**: `api/orders.py:68-69`, `api/positions.py:55-58`, `core/binance_client.py:85-88`
```python
'quantity': float(order.quantity)  # Numeric → float
'price': float(order.price)  # Numeric → float
total_balance = float(usdt_asset.get('walletBalance', 0))  # str → float
```
**数量**: 约30处
**风险**: 🔴 高（精度丢失）

#### ❌ 直接计算（高风险）
**文件**: `api/system.py:58`
```python
total_pnl = sum(float(pos.unrealized_pnl or 0) for pos in positions)
```
**数量**: 约10处
**风险**: 🔴 高（精度丢失）

---

## 2. 列出所有金额计算代码

### 计算1: 持仓盈亏计算
**文件**: `core/trade_executor.py` (未找到计算代码)
**问题**: ❌ 未找到持仓盈亏计算代码

### 计算2: 保证金计算
**文件**: `core/trade_executor.py:468-471`
```python
required_margin = (quantity * price) / leverage
if available_balance < required_margin:
    # 拒绝下单
```
**问题**: 
- ❌ quantity和price是什么类型？
- ❌ 如果是float，精度丢失
- ❌ 如果是Numeric，除法后是什么类型？

### 计算3: 止盈止损价格计算
**文件**: `core/trade_executor.py:408-414`
```python
tp_price = entry_price * (1 + instance.take_profit / 100)
sl_price = entry_price * (1 - instance.stop_loss / 100)
```
**问题**:
- ❌ entry_price是Numeric
- ❌ instance.take_profit是Float（database.py:158）
- ❌ Numeric * Float = ?
- ❌ 精度不确定

### 计算4: 资金门禁计算
**文件**: `core/trade_executor.py:468-471`
```python
required_margin = (quantity * price) / leverage
```
**问题**: 同计算2

---

## 3. 验证是否全部使用Decimal

### ❌ 未全部使用Decimal

#### 使用Decimal的地方
**文件**: `core/mock/mock_exchange.py:69-77`
```python
self.balance: Decimal = Decimal("10000.0")
self.prices: Dict[str, Decimal] = {
    "BTC/USDT": Decimal("50000.0"),
}
```
**范围**: 仅Mock代码

#### 未使用Decimal的地方
**文件**: `core/trade_executor.py`, `core/binance_client.py`, `api/*.py`
**问题**: 
- ❌ 所有业务代码都未使用Decimal
- ❌ 所有计算都是float或Numeric
- ❌ Numeric和float混合计算，精度不确定

---

## 4. 验证数据库是否Numeric精度

### ✅ 部分字段使用Numeric
**文件**: `core/database.py`

#### 使用Numeric的字段（正确）
- 行77-78: Account.initial_balance, current_balance - `Numeric(20, 8)`
- 行95: FundConfig.initial_capital - `Numeric(20, 8)`
- 行99-100: FundConfig.compound_ratio, current_base - `Numeric(10, 4)`, `Numeric(20, 8)`
- 行188-191: Order.quantity, filled_quantity, price, average_price - `Numeric(20, 8)`
- 行210-216: Position.quantity, entry_price, current_price, unrealized_pnl, take_profit, stop_loss - `Numeric(20, 8)`

#### ❌ 使用Float的字段（错误）
- 行104-105: FundConfig.threshold, multiple - `Float`
- 行109: FundConfig.protect_multiplier - `Float`
- 行112: FundConfig.last_protect_balance - `Float`
- 行116: FundConfig.endpoint_multiplier - `Float`
- 行121: FundConfig.replenish_min_amount - `Float`
- 行123: FundConfig.replenish_alert_threshold - `Float`
- 行125: FundConfig.total_replenished_amount - `Float`
- 行158-159: Instance.take_profit, stop_loss - `Float`
- 行164: Instance.trailing_stop_percent - `Float`

**问题**:
1. 资金管理相关字段使用Float
2. 止盈止损百分比使用Float
3. **Float精度不足，可能导致资金误差**

---

## 5. 验证下单金额是否按exchange filters截断

### ❌ 未找到exchange filters截断代码

**搜索结果**:
```bash
grep -rn "filters\|stepSize\|minQty\|maxQty" backend/
# 结果：无匹配
```

**问题**:
1. 未从exchangeInfo读取filters
2. 未按stepSize截断数量
3. 未按tickSize截断价格
4. **下单可能因精度不符合交易所要求而失败**

**正确做法**:
```python
# 1. 读取exchangeInfo
exchange_info = await client.fetch_exchange_info(symbol)
filters = exchange_info['filters']

# 2. 获取stepSize
lot_size_filter = next(f for f in filters if f['filterType'] == 'LOT_SIZE')
step_size = Decimal(lot_size_filter['stepSize'])

# 3. 截断数量
quantity = (quantity // step_size) * step_size

# 4. 获取tickSize
price_filter = next(f for f in filters if f['filterType'] == 'PRICE_FILTER')
tick_size = Decimal(price_filter['tickSize'])

# 5. 截断价格
price = (price // tick_size) * tick_size
```

---

## 6. 标记所有float运算

### float运算位置

#### 位置1: API返回值转换
**文件**: `api/orders.py:68-69`
```python
'quantity': float(order.quantity),
'price': float(order.price) if order.price else None,
```
**风险**: 🔴 Numeric → float，精度丢失

#### 位置2: 持仓数据转换
**文件**: `api/positions.py:55-58`
```python
'quantity': float(pos.quantity),
'entry_price': float(pos.entry_price),
'current_price': float(pos.current_price) if pos.current_price else float(pos.entry_price),
'unrealized_pnl': float(pos.unrealized_pnl) if pos.unrealized_pnl else 0,
```
**风险**: 🔴 Numeric → float，精度丢失

#### 位置3: 余额读取
**文件**: `core/binance_client.py:85-88`
```python
total_balance = float(usdt_asset.get('walletBalance', 0))
available_balance = float(usdt_asset.get('availableBalance', 0))
margin_balance = float(usdt_asset.get('marginBalance', 0))
unrealized_pnl = float(usdt_asset.get('unrealizedProfit', 0))
```
**风险**: 🔴 str → float，精度丢失

#### 位置4: 持仓数据读取
**文件**: `core/binance_client.py:154-157`
```python
'size': float(pos.get('contracts', 0)),
'entry_price': float(pos.get('entryPrice', 0)),
'mark_price': float(pos.get('markPrice', 0)),
'liquidation_price': float(pos.get('liquidationPrice', 0)),
```
**风险**: 🔴 str → float，精度丢失

#### 位置5: 盈亏汇总
**文件**: `api/system.py:58`
```python
total_pnl = sum(float(pos.unrealized_pnl or 0) for pos in positions)
```
**风险**: 🔴 Numeric → float → sum，精度丢失

---

## 7. P0阻塞清单

### P0-18: 大量float类型转换导致精度丢失
**文件**: `api/orders.py:68-69`, `api/positions.py:55-58`, `core/binance_client.py:85-88`
**问题**: Numeric → float，精度丢失
**影响**: 
- 订单数量精度丢失
- 持仓数量精度丢失
- 余额精度丢失
- **可能导致资金误差**

### P0-19: 数据库字段使用Float
**文件**: `core/database.py:104-125, 158-164`
**问题**: 资金管理和止盈止损字段使用Float
**影响**: 
- 资金计算精度不足
- 止盈止损价格精度不足
- **可能导致资金误差**

### P0-20: 未按exchange filters截断
**文件**: 全局搜索无结果
**问题**: 未从exchangeInfo读取filters，未截断数量和价格
**影响**: 
- 下单可能因精度不符合交易所要求而失败
- **下单失败率高**

### P0-21: Numeric和Float混合计算
**文件**: `core/trade_executor.py:408-414, 468-471`
**问题**: Numeric * Float，精度不确定
**影响**: 
- 止盈止损价格计算精度不确定
- 保证金计算精度不确定
- **可能导致资金误差**

---

## 8. 最终结论

### ❌ 第3层审计失败：精度安全无法保证

**失败原因**:
1. **大量float类型转换**（30+处）
2. **数据库字段使用Float**（10+个字段）
3. **未按exchange filters截断**（完全缺失）
4. **Numeric和Float混合计算**（精度不确定）

**具体文件+行号**:
- api/orders.py:68-69 - Numeric → float
- api/positions.py:55-58 - Numeric → float
- core/binance_client.py:85-88, 154-157 - str → float
- api/system.py:58 - Numeric → float → sum
- core/database.py:104-125, 158-164 - 字段使用Float
- 全局 - 未找到exchange filters截断代码
- core/trade_executor.py:408-414, 468-471 - Numeric * Float

**系统判定**: 
# ❌ 系统不可实盘
# 原因：精度丢失可能导致资金误差，下单可能因精度不符合交易所要求而失败
