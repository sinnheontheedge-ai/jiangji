# 资金监控器逻辑修正

## 修正1: 盈利倍数终点 - 不停止实例（循环执行）

### 当前代码（第440-444行）
```python
# 停止实例
instance.status = "stopped"
await db.commit()

logger.info(f"🛑 实例 {instance.id} 已停止（达到盈利倍数终点）")
```

### 修正后代码
```python
# 更新触发次数（循环执行，不停止实例）
fund_config.endpoint_count += 1
await db.commit()

logger.info(f"✅ 盈利倍数终点提取成功（第{fund_config.endpoint_count}次），继续交易")
```

### 完整修正后的_check_profit_endpoint方法
```python
async def _check_profit_endpoint(self, fund_config: FundConfig, wallet_balance: float,
                                client: any, db: AsyncSession):
    """检查盈利倍数终点"""
    try:
        # 计算终点阈值 = 初始投入金额 × 终点倍数
        endpoint_threshold = fund_config.initial_capital * fund_config.endpoint_multiplier
        
        # 如果余额达到终点阈值
        if wallet_balance >= endpoint_threshold:
            # 计算提取金额 = 当前余额 - 初始投入金额
            extract_amount = wallet_balance - fund_config.initial_capital
            
            if extract_amount > 0:
                logger.info(f"🏁 盈利倍数终点触发: 账户={fund_config.account_id}, 提取={extract_amount}")
                
                # 执行划转
                try:
                    transfer_result = await client.transfer(
                        asset="USDT",
                        amount=extract_amount,
                        from_account="UMFUTURE",
                        to_account="SPOT"  # 转到现货账户
                    )
                    
                    logger.info(f"✅ 盈利倍数终点提取成功: {transfer_result}")
                    
                    # 更新触发次数（循环执行，不停止实例）
                    fund_config.endpoint_count += 1
                    await db.commit()
                    
                    logger.info(f"✅ 盈利倍数终点提取成功（第{fund_config.endpoint_count}次），继续交易")
                    
                    # 发布事件
                    await self.event_bus.publish(
                        f"fund:profit_endpoint_reached:{fund_config.account_id}",
                        {
                            "account_id": fund_config.account_id,
                            "amount": extract_amount,
                            "endpoint_multiplier": fund_config.endpoint_multiplier,
                            "count": fund_config.endpoint_count
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"❌ 盈利倍数终点提取失败: {e}")
        
    except Exception as e:
        logger.error(f"❌ 盈利倍数终点检查失败: {e}")
```

---

## 修正2: 初始金额保护 - 重新实现触发逻辑

### 当前代码（第368-378行）
```python
# 计算保护阈值
protect_threshold = instance.initial_amount * instance.protect_multiplier

# 如果余额达到保护阈值
if wallet_balance >= protect_threshold:
    # 计算提取金额（保留初始金额）
    extract_amount = wallet_balance - instance.initial_amount
    
    # 按步长截断
    if instance.transfer_step:
        extract_amount = (extract_amount // instance.transfer_step) * instance.transfer_step
```

### 修正后代码
```python
# 计算保护阈值
if fund_config.protect_count == 0:
    # 第1次触发点 = 初始投入金额 × 保护倍数
    protect_threshold = fund_config.initial_capital * fund_config.protect_multiplier
else:
    # 第N次触发点 = 上次保护后的余额 + 初始投入金额
    protect_threshold = fund_config.last_protect_balance + fund_config.initial_capital

# 如果余额达到保护阈值
if wallet_balance >= protect_threshold:
    # 每次转移固定金额 = 初始投入金额
    extract_amount = fund_config.initial_capital
```

### 完整修正后的_check_initial_protect方法
```python
async def _check_initial_protect(self, fund_config: FundConfig, wallet_balance: float,
                                client: any, db: AsyncSession):
    """检查初始金额保护"""
    try:
        # 检查是否达到最大保护次数
        if fund_config.protect_count >= fund_config.max_protect_count:
            # 已达到最大次数，自动禁用保护
            if fund_config.enable_initial_protect:
                fund_config.enable_initial_protect = False
                await db.commit()
                logger.info(f"🛡️ 初始金额保护已达到最大次数({fund_config.max_protect_count})，自动禁用")
            return
        
        # 计算保护阈值
        if fund_config.protect_count == 0:
            # 第1次触发点 = 初始投入金额 × 保护倍数
            protect_threshold = fund_config.initial_capital * fund_config.protect_multiplier
        else:
            # 第N次触发点 = 上次保护后的余额 + 初始投入金额
            protect_threshold = fund_config.last_protect_balance + fund_config.initial_capital
        
        # 如果余额达到保护阈值
        if wallet_balance >= protect_threshold:
            # 每次转移固定金额 = 初始投入金额
            extract_amount = fund_config.initial_capital
            
            logger.info(f"🛡️ 初始金额保护触发: 账户={fund_config.account_id}, 提取={extract_amount}, 第{fund_config.protect_count + 1}次")
            
            # 执行划转
            try:
                transfer_result = await client.transfer(
                    asset="USDT",
                    amount=extract_amount,
                    from_account="UMFUTURE",
                    to_account="SPOT"  # 转到现货账户
                )
                
                logger.info(f"✅ 初始金额保护提取成功: {transfer_result}")
                
                # 更新触发次数和余额
                fund_config.protect_count += 1
                fund_config.last_protect_balance = wallet_balance - extract_amount
                
                # 检查是否达到最大次数
                if fund_config.protect_count >= fund_config.max_protect_count:
                    fund_config.enable_initial_protect = False
                    logger.info(f"🛡️ 初始金额保护已达到最大次数({fund_config.max_protect_count})，自动禁用")
                
                await db.commit()
                
                # 发布事件
                await self.event_bus.publish(
                    f"fund:initial_protected:{fund_config.account_id}",
                    {
                        "account_id": fund_config.account_id,
                        "amount": extract_amount,
                        "protect_multiplier": fund_config.protect_multiplier,
                        "count": fund_config.protect_count,
                        "last_balance": fund_config.last_protect_balance
                    }
                )
                
            except Exception as e:
                logger.error(f"❌ 初始金额保护提取失败: {e}")
        
    except Exception as e:
        logger.error(f"❌ 初始金额保护检查失败: {e}")
```

---

## 修正3: 复利系统 - 阶段重置逻辑

### 需要确认的逻辑
盈利提取后，如果是阶段复利模式，需要重置current_base到initial_capital

### 修正位置
在盈利提取成功后，添加复利重置逻辑：

```python
# 在盈利提取成功后
if fund_config.compounding_mode == "stage":
    # 阶段复利模式：重置复利起点到初始投入金额
    fund_config.current_base = fund_config.initial_capital
    await db.commit()
    logger.info(f"📈 阶段复利重置: current_base → {fund_config.initial_capital}")
```

---

## 关键变更总结

### 1. 盈利倍数终点
- ❌ 删除：停止实例的代码
- ✅ 新增：更新endpoint_count计数器
- ✅ 修改：循环执行，不停止实例

### 2. 初始金额保护
- ❌ 删除：transfer_step步长逻辑
- ❌ 删除：每次提取全部盈利的逻辑
- ✅ 新增：protect_count触发次数追踪
- ✅ 新增：last_protect_balance余额追踪
- ✅ 修改：触发点计算公式（第1次 vs 第N次）
- ✅ 修改：每次提取固定金额（initial_capital）
- ✅ 新增：达到最大次数自动禁用

### 3. 复利系统
- ✅ 新增：盈利提取后重置current_base（阶段模式）

### 4. 字段引用
- ❌ 删除：instance.initial_amount → fund_config.initial_capital
- ❌ 删除：instance.transfer_step → 不再使用
- ❌ 删除：instance.endpoint_triggered → fund_config.endpoint_count
- ✅ 新增：fund_config.protect_count
- ✅ 新增：fund_config.last_protect_balance
