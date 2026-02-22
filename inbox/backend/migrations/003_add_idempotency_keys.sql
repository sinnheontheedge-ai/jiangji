-- 幂等键表
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id SERIAL PRIMARY KEY,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_data JSONB,
    status VARCHAR(50) NOT NULL,  -- processing/completed/failed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    
    -- 索引
    INDEX idx_key (idempotency_key),
    INDEX idx_expires (expires_at),
    INDEX idx_status (status)
);

-- 添加注释
COMMENT ON TABLE idempotency_keys IS '幂等键表';
COMMENT ON COLUMN idempotency_keys.idempotency_key IS '幂等键（UUID）';
COMMENT ON COLUMN idempotency_keys.request_hash IS '请求哈希（SHA256）';
COMMENT ON COLUMN idempotency_keys.response_data IS '响应数据（JSON格式）';
COMMENT ON COLUMN idempotency_keys.status IS '状态（processing/completed/failed）';
COMMENT ON COLUMN idempotency_keys.expires_at IS '过期时间';
