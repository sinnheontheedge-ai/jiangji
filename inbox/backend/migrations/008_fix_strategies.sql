-- 修复strategies表，添加缺失的parameters字段

ALTER TABLE strategies ADD COLUMN IF NOT EXISTS parameters JSONB;

COMMENT ON COLUMN strategies.parameters IS '策略参数（JSON格式）';
