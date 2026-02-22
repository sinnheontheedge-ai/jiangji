-- 状态转换历史表
CREATE TABLE IF NOT EXISTS state_transitions (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,  -- instance/order/position
    entity_id INTEGER NOT NULL,
    from_state VARCHAR(50) NOT NULL,
    to_state VARCHAR(50) NOT NULL,
    reason TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- 索引
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_created_at (created_at)
);

-- 添加注释
COMMENT ON TABLE state_transitions IS '状态转换历史表';
COMMENT ON COLUMN state_transitions.entity_type IS '实体类型（instance/order/position）';
COMMENT ON COLUMN state_transitions.entity_id IS '实体ID';
COMMENT ON COLUMN state_transitions.from_state IS '源状态';
COMMENT ON COLUMN state_transitions.to_state IS '目标状态';
COMMENT ON COLUMN state_transitions.reason IS '转换原因';
COMMENT ON COLUMN state_transitions.metadata IS '附加元数据（JSON格式）';
