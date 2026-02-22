-- ========================================
-- 资金管理模块数据库迁移脚本
-- 日期: 2026-02-20
-- 目的: 统一初始投入金额，删除冗余字段，添加必要字段
-- ========================================

-- ========================================
-- 第1步: 添加新字段
-- ========================================

-- 添加全局初始投入金额字段
ALTER TABLE fund_configs ADD COLUMN initial_capital DECIMAL(20,8) NOT NULL DEFAULT 1000.0 COMMENT '全局初始投入金额';

-- 添加初始金额保护已触发次数字段
ALTER TABLE fund_configs ADD COLUMN protect_count INTEGER NOT NULL DEFAULT 0 COMMENT '初始金额保护已触发次数';

-- 添加上次保护后的余额字段
ALTER TABLE fund_configs ADD COLUMN last_protect_balance DECIMAL(20,8) NULL COMMENT '上次保护后的余额';

-- ========================================
-- 第2步: 数据迁移（保留现有数据）
-- ========================================

-- 将 initial_base 的值迁移到 initial_capital
UPDATE fund_configs SET initial_capital = initial_base WHERE initial_base IS NOT NULL;

-- 将 protection_count 的值迁移到 protect_count
UPDATE fund_configs SET protect_count = protection_count WHERE protection_count IS NOT NULL;

-- ========================================
-- 第3步: 删除冗余字段
-- ========================================

-- 删除复利相关冗余字段
ALTER TABLE fund_configs DROP COLUMN initial_base;  -- 与initial_capital重复

-- 删除盈利提取相关冗余字段
ALTER TABLE fund_configs DROP COLUMN initial_margin;  -- 使用initial_capital
ALTER TABLE fund_configs DROP COLUMN max_extract_ratio;  -- 无意义

-- 删除初始金额保护相关冗余字段
ALTER TABLE fund_configs DROP COLUMN protection_initial_amount;  -- 使用initial_capital
ALTER TABLE fund_configs DROP COLUMN protection_transfer_step;  -- 无意义
ALTER TABLE fund_configs DROP COLUMN protection_count;  -- 已迁移到protect_count

-- 删除盈利倍数终点相关冗余字段
ALTER TABLE fund_configs DROP COLUMN endpoint_initial_amount;  -- 使用initial_capital
ALTER TABLE fund_configs DROP COLUMN endpoint_transfer_step;  -- 无意义

-- 删除自动补足余额相关冗余字段
ALTER TABLE fund_configs DROP COLUMN replenish_initial_capital;  -- 使用initial_capital
ALTER TABLE fund_configs DROP COLUMN replenish_check_interval;  -- 使用WebSocket

-- ========================================
-- 第4步: 移除字段约束（允许无上限）
-- ========================================

-- 注意: MySQL不支持直接修改CHECK约束，需要先删除再添加
-- 如果之前有CHECK约束，需要先删除
-- ALTER TABLE fund_configs DROP CONSTRAINT chk_endpoint_multiple;
-- ALTER TABLE fund_configs DROP CONSTRAINT chk_replenish_max_per_day;

-- 修改字段类型，确保可以存储任意正数
ALTER TABLE fund_configs MODIFY COLUMN endpoint_multiple FLOAT NULL COMMENT '终点倍数（无上限）';
ALTER TABLE fund_configs MODIFY COLUMN replenish_max_per_day INTEGER NULL COMMENT '每日最大补足次数（无上限）';

-- ========================================
-- 第5步: 重命名字段（保持一致性）
-- ========================================

-- 将 protection_enabled 重命名为 enable_initial_protect（与需求文档一致）
ALTER TABLE fund_configs CHANGE COLUMN protection_enabled enable_initial_protect BOOLEAN DEFAULT FALSE COMMENT '是否启用初始金额保护';

-- 将 protection_multiple 重命名为 protect_multiplier（与需求文档一致）
ALTER TABLE fund_configs CHANGE COLUMN protection_multiple protect_multiplier FLOAT NULL COMMENT '保护倍数';

-- 将 protection_max_count 重命名为 max_protect_count（与需求文档一致）
ALTER TABLE fund_configs CHANGE COLUMN protection_max_count max_protect_count INTEGER NULL COMMENT '最大保护次数';

-- 将 endpoint_enabled 重命名为 enable_endpoint（与需求文档一致）
ALTER TABLE fund_configs CHANGE COLUMN endpoint_enabled enable_endpoint BOOLEAN DEFAULT FALSE COMMENT '是否启用盈利倍数终点';

-- 将 endpoint_multiple 重命名为 endpoint_multiplier（与需求文档一致）
ALTER TABLE fund_configs CHANGE COLUMN endpoint_multiple endpoint_multiplier FLOAT NULL COMMENT '终点倍数（无上限）';

-- 将 endpoint_triggered 重命名为 endpoint_count（与需求文档一致，改为计数器）
ALTER TABLE fund_configs CHANGE COLUMN endpoint_triggered endpoint_count INTEGER DEFAULT 0 COMMENT '终点触发次数（循环执行）';

-- 将 replenish_enabled 重命名为 enable_replenish（与需求文档一致）
ALTER TABLE fund_configs CHANGE COLUMN replenish_enabled enable_replenish BOOLEAN DEFAULT FALSE COMMENT '是否启用自动补足余额';

-- ========================================
-- 验证迁移结果
-- ========================================

-- 查看表结构
-- DESCRIBE fund_configs;

-- 查看数据
-- SELECT * FROM fund_configs LIMIT 10;
