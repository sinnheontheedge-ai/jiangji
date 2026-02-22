-- Saga日志表
CREATE TABLE IF NOT EXISTS saga_logs (
    id SERIAL PRIMARY KEY,
    saga_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,  -- pending/executing/completed/compensating/compensated/failed
    step_count INTEGER NOT NULL,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    failed_at TIMESTAMP,
    compensate_started_at TIMESTAMP,
    compensate_completed_at TIMESTAMP,
    
    -- 索引
    INDEX idx_saga_id (saga_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Saga步骤日志表
CREATE TABLE IF NOT EXISTS saga_step_logs (
    id SERIAL PRIMARY KEY,
    saga_id VARCHAR(255) NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- success/failed/compensated/compensate_failed
    result JSONB,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- 索引
    INDEX idx_saga_id (saga_id),
    INDEX idx_step_name (step_name),
    INDEX idx_created_at (created_at),
    
    -- 外键
    FOREIGN KEY (saga_id) REFERENCES saga_logs(saga_id) ON DELETE CASCADE
);

-- 添加注释
COMMENT ON TABLE saga_logs IS 'Saga日志表';
COMMENT ON COLUMN saga_logs.saga_id IS 'Saga唯一标识';
COMMENT ON COLUMN saga_logs.status IS '状态（pending/executing/completed/compensating/compensated/failed）';
COMMENT ON COLUMN saga_logs.step_count IS '步骤总数';

COMMENT ON TABLE saga_step_logs IS 'Saga步骤日志表';
COMMENT ON COLUMN saga_step_logs.saga_id IS 'Saga唯一标识';
COMMENT ON COLUMN saga_step_logs.step_name IS '步骤名称';
COMMENT ON COLUMN saga_step_logs.status IS '状态（success/failed/compensated/compensate_failed）';
COMMENT ON COLUMN saga_step_logs.result IS '执行结果（JSON格式）';
