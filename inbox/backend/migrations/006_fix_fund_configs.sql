-- 修复fund_configs表结构，使其与ORM模型完全一致
-- 此脚本将删除旧表并重新创建

DROP TABLE IF EXISTS fund_configs CASCADE;

CREATE TABLE fund_configs (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
    
    -- 复利配置
    compounding_mode VARCHAR(20) NOT NULL DEFAULT 'stage',
    compound_ratio FLOAT NOT NULL DEFAULT 20.0,
    initial_base FLOAT NOT NULL DEFAULT 1000.0,
    current_base FLOAT NOT NULL DEFAULT 1000.0,
    position_percent FLOAT NOT NULL DEFAULT 10.0,
    concurrent_positions INTEGER NOT NULL DEFAULT 1,
    
    -- 盈利提取配置
    extraction_mode VARCHAR(20) NOT NULL DEFAULT 'wallet_threshold',
    initial_margin FLOAT NOT NULL DEFAULT 1000.0,
    threshold FLOAT,
    multiple FLOAT,
    max_extract_ratio FLOAT,
    
    -- 初始金额保护配置
    protection_enabled BOOLEAN DEFAULT FALSE,
    protection_initial_amount FLOAT,
    protection_multiple FLOAT,
    protection_max_count INTEGER,
    protection_transfer_step FLOAT,
    protection_count INTEGER DEFAULT 0,
    
    -- 盈利倍数终点配置
    endpoint_enabled BOOLEAN DEFAULT FALSE,
    endpoint_initial_amount FLOAT,
    endpoint_multiple FLOAT,
    endpoint_transfer_step FLOAT,
    endpoint_triggered BOOLEAN DEFAULT FALSE,
    
    -- 自动补足余额配置
    replenish_enabled BOOLEAN DEFAULT FALSE,
    replenish_initial_capital FLOAT,
    replenish_check_interval INTEGER DEFAULT 60,
    replenish_min_amount FLOAT DEFAULT 10,
    replenish_enable_alert BOOLEAN DEFAULT TRUE,
    replenish_alert_threshold FLOAT DEFAULT 0.8,
    replenish_max_per_day INTEGER DEFAULT 10,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 添加注释
COMMENT ON TABLE fund_configs IS '资金管理配置表';
COMMENT ON COLUMN fund_configs.account_id IS '关联账户ID';
COMMENT ON COLUMN fund_configs.compounding_mode IS '复利模式: stage/perpetual';
COMMENT ON COLUMN fund_configs.compound_ratio IS '复利比例 (%)';
COMMENT ON COLUMN fund_configs.initial_base IS '初始复利起点';
COMMENT ON COLUMN fund_configs.current_base IS '当前复利起点';
COMMENT ON COLUMN fund_configs.position_percent IS '仓位百分比 (%)';
COMMENT ON COLUMN fund_configs.concurrent_positions IS '并发仓位数';
COMMENT ON COLUMN fund_configs.extraction_mode IS '提取模式: wallet_threshold/multiple_mode';
COMMENT ON COLUMN fund_configs.initial_margin IS '初始保证金';
COMMENT ON COLUMN fund_configs.threshold IS '提取阈值(钱包阈值模式)';
COMMENT ON COLUMN fund_configs.multiple IS '提取倍数(倍数模式)';
COMMENT ON COLUMN fund_configs.max_extract_ratio IS '最大提取比例';
COMMENT ON COLUMN fund_configs.protection_enabled IS '是否启用初始金额保护';
COMMENT ON COLUMN fund_configs.protection_initial_amount IS '保护初始金额';
COMMENT ON COLUMN fund_configs.protection_multiple IS '保护倍数';
COMMENT ON COLUMN fund_configs.protection_max_count IS '最大保护次数';
COMMENT ON COLUMN fund_configs.protection_transfer_step IS '划转步长';
COMMENT ON COLUMN fund_configs.protection_count IS '已执行保护次数';
COMMENT ON COLUMN fund_configs.endpoint_enabled IS '是否启用盈利倍数终点';
COMMENT ON COLUMN fund_configs.endpoint_initial_amount IS '终点初始金额';
COMMENT ON COLUMN fund_configs.endpoint_multiple IS '终点倍数';
COMMENT ON COLUMN fund_configs.endpoint_transfer_step IS '终点划转步长';
COMMENT ON COLUMN fund_configs.endpoint_triggered IS '是否已触发终点';
COMMENT ON COLUMN fund_configs.replenish_enabled IS '是否启用自动补足余额';
COMMENT ON COLUMN fund_configs.replenish_initial_capital IS '初始资金';
COMMENT ON COLUMN fund_configs.replenish_check_interval IS '检查间隔(秒)';
COMMENT ON COLUMN fund_configs.replenish_min_amount IS '最小转账金额';
COMMENT ON COLUMN fund_configs.replenish_enable_alert IS '启用余额不足告警';
COMMENT ON COLUMN fund_configs.replenish_alert_threshold IS '告警阈值(百分比)';
COMMENT ON COLUMN fund_configs.replenish_max_per_day IS '每日最大补足次数';
