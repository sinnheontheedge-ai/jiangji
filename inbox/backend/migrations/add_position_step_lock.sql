-- 创建持仓Step Lock状态表
CREATE TABLE IF NOT EXISTS position_step_locks (
    id SERIAL PRIMARY KEY,
    position_id INTEGER UNIQUE NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    current_level INTEGER DEFAULT 0 COMMENT '当前档位（0表示未触发任何档位）',
    levels_config JSON COMMENT '档位配置',
    peak_price DECIMAL(20, 8) COMMENT '峰值价格',
    last_check_time TIMESTAMP COMMENT '上次检查时间',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW() ON UPDATE NOW()
);

CREATE INDEX idx_position_step_locks_position_id ON position_step_locks(position_id);

-- 添加注释
COMMENT ON TABLE position_step_locks IS '持仓Step Lock状态表';
COMMENT ON COLUMN position_step_locks.current_level IS '当前档位（0表示未触发任何档位）';
COMMENT ON COLUMN position_step_locks.levels_config IS '档位配置JSON';
COMMENT ON COLUMN position_step_locks.peak_price IS '峰值价格';
COMMENT ON COLUMN position_step_locks.last_check_time IS '上次检查时间';
