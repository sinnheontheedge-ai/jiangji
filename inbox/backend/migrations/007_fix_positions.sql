-- 修复positions表，添加缺失的leverage字段

ALTER TABLE positions ADD COLUMN IF NOT EXISTS leverage INTEGER DEFAULT 1;

COMMENT ON COLUMN positions.leverage IS '杠杆倍数';
