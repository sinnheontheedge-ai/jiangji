-- 添加代理配置字段
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS proxy_config JSONB;

-- 添加注释
COMMENT ON COLUMN accounts.proxy_config IS '代理配置（JSON格式，包含host和port）';
