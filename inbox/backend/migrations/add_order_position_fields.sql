-- 为Order表添加account_id和position_id字段
ALTER TABLE orders ADD COLUMN account_id INTEGER NOT NULL COMMENT '账户ID';
ALTER TABLE orders ADD COLUMN position_id INTEGER NULL COMMENT '关联持仓ID';
ALTER TABLE orders ADD CONSTRAINT fk_orders_account FOREIGN KEY (account_id) REFERENCES accounts(id);
ALTER TABLE orders ADD CONSTRAINT fk_orders_position FOREIGN KEY (position_id) REFERENCES positions(id);

-- 为Position表添加account_id、take_profit和stop_loss字段
ALTER TABLE positions ADD COLUMN account_id INTEGER NOT NULL COMMENT '账户ID';
ALTER TABLE positions ADD COLUMN take_profit FLOAT NULL COMMENT '止盈价格';
ALTER TABLE positions ADD COLUMN stop_loss FLOAT NULL COMMENT '止损价格';
ALTER TABLE positions ADD CONSTRAINT fk_positions_account FOREIGN KEY (account_id) REFERENCES accounts(id);
