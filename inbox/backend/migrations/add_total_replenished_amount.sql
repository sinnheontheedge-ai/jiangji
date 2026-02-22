-- 添加累计补足金额字段到fund_configs表
-- 日期: 2026-02-20
-- 模块: 自动补足余额（模块04）

-- 添加字段
ALTER TABLE fund_configs 
ADD COLUMN total_replenished_amount DECIMAL(20, 8) DEFAULT 0.0 COMMENT '累计补足金额（未覆盖部分）';

-- 说明：
-- 1. 此字段用于追踪账户级别的累计补足金额
-- 2. 单仓模式：平仓后亏损时补足，盈利时不处理
-- 3. 并发模式：亏损时累加，盈利时扣减（覆盖）
-- 4. 账户级别：一个账户一个累计值，不是每个实例一个
