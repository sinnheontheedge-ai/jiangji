-- ==========================================
-- 完整数据库迁移脚本 (PostgreSQL)
-- 基于ORM模型自动生成
-- ==========================================

-- 删除所有表（如果存在）
DROP TABLE IF EXISTS position_step_locks CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS instances CASCADE;
DROP TABLE IF EXISTS fund_configs CASCADE;
DROP TABLE IF EXISTS system_configs CASCADE;
DROP TABLE IF EXISTS strategies CASCADE;
DROP TABLE IF EXISTS state_transitions CASCADE;
DROP TABLE IF EXISTS saga_logs CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS notification_configs CASCADE;
DROP TABLE IF EXISTS idempotency_keys CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;

-- 创建所有表


CREATE TABLE accounts (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	exchange VARCHAR(50) NOT NULL, 
	api_key VARCHAR(200) NOT NULL, 
	api_secret VARCHAR(200) NOT NULL, 
	testnet BOOLEAN, 
	proxy_config JSON, 
	initial_balance FLOAT NOT NULL, 
	current_balance FLOAT NOT NULL, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE idempotency_keys (
	id SERIAL NOT NULL, 
	key VARCHAR(255) NOT NULL, 
	response TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (key)
)

;


CREATE TABLE notification_configs (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	type VARCHAR(50) NOT NULL, 
	config JSON NOT NULL, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE notifications (
	id SERIAL NOT NULL, 
	type VARCHAR(50) NOT NULL, 
	config JSON NOT NULL, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE saga_logs (
	id SERIAL NOT NULL, 
	saga_id VARCHAR(100) NOT NULL, 
	step_name VARCHAR(100) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	input_data JSON, 
	output_data JSON, 
	error_message TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE state_transitions (
	id SERIAL NOT NULL, 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id INTEGER NOT NULL, 
	from_state VARCHAR(50), 
	to_state VARCHAR(50) NOT NULL, 
	reason TEXT, 
	extra_data JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE strategies (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	code TEXT NOT NULL, 
	parameters JSON, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE system_configs (
	id SERIAL NOT NULL, 
	key VARCHAR(100) NOT NULL, 
	value TEXT NOT NULL, 
	description TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (key)
)

;


CREATE TABLE fund_configs (
	id SERIAL NOT NULL, 
	account_id INTEGER NOT NULL, 
	initial_capital FLOAT NOT NULL, 
	compounding_mode VARCHAR(20) NOT NULL, 
	compound_ratio FLOAT NOT NULL, 
	current_base FLOAT NOT NULL, 
	extraction_mode VARCHAR(20) NOT NULL, 
	threshold FLOAT, 
	multiple FLOAT, 
	enable_initial_protect BOOLEAN, 
	protect_multiplier FLOAT, 
	max_protect_count INTEGER, 
	protect_count INTEGER, 
	last_protect_balance FLOAT, 
	enable_endpoint BOOLEAN, 
	endpoint_multiplier FLOAT, 
	endpoint_count INTEGER, 
	enable_replenish BOOLEAN, 
	replenish_min_amount FLOAT, 
	replenish_enable_alert BOOLEAN, 
	replenish_alert_threshold FLOAT, 
	replenish_max_per_day INTEGER, 
	total_replenished_amount FLOAT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (account_id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE CASCADE
)

;


CREATE TABLE instances (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	account_id INTEGER NOT NULL, 
	strategy_id INTEGER NOT NULL, 
	symbols JSON NOT NULL, 
	timeframe VARCHAR(20) NOT NULL, 
	take_profit FLOAT, 
	stop_loss FLOAT, 
	position_mode VARCHAR(20), 
	use_step_locking BOOLEAN, 
	step_config JSON, 
	enable_trailing_stop BOOLEAN, 
	trailing_stop_percent FLOAT, 
	leverage INTEGER, 
	status VARCHAR(20), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id), 
	FOREIGN KEY(strategy_id) REFERENCES strategies (id)
)

;


CREATE TABLE positions (
	id SERIAL NOT NULL, 
	instance_id INTEGER NOT NULL, 
	account_id INTEGER NOT NULL, 
	symbol VARCHAR(50) NOT NULL, 
	side VARCHAR(10) NOT NULL, 
	quantity FLOAT NOT NULL, 
	entry_price FLOAT NOT NULL, 
	current_price FLOAT, 
	unrealized_pnl FLOAT, 
	leverage INTEGER, 
	take_profit FLOAT, 
	stop_loss FLOAT, 
	is_open BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(instance_id) REFERENCES instances (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;


CREATE TABLE orders (
	id SERIAL NOT NULL, 
	instance_id INTEGER NOT NULL, 
	account_id INTEGER NOT NULL, 
	position_id INTEGER, 
	exchange_order_id VARCHAR(100), 
	symbol VARCHAR(50) NOT NULL, 
	side VARCHAR(10) NOT NULL, 
	order_type VARCHAR(20) NOT NULL, 
	quantity FLOAT NOT NULL, 
	price FLOAT, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(instance_id) REFERENCES instances (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id), 
	FOREIGN KEY(position_id) REFERENCES positions (id), 
	UNIQUE (exchange_order_id)
)

;


CREATE TABLE position_step_locks (
	id SERIAL NOT NULL, 
	position_id INTEGER NOT NULL, 
	current_level INTEGER, 
	levels_config JSON, 
	peak_price FLOAT, 
	last_check_time TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (position_id), 
	FOREIGN KEY(position_id) REFERENCES positions (id) ON DELETE CASCADE
)

;

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_accounts_id ON accounts (id);
CREATE INDEX IF NOT EXISTS ix_idempotency_keys_id ON idempotency_keys (id);
CREATE INDEX IF NOT EXISTS ix_notification_configs_id ON notification_configs (id);
CREATE INDEX IF NOT EXISTS ix_notifications_id ON notifications (id);
CREATE INDEX IF NOT EXISTS ix_saga_logs_id ON saga_logs (id);
CREATE INDEX IF NOT EXISTS ix_state_transitions_id ON state_transitions (id);
CREATE INDEX IF NOT EXISTS ix_strategies_id ON strategies (id);
CREATE INDEX IF NOT EXISTS ix_system_configs_id ON system_configs (id);
CREATE INDEX IF NOT EXISTS ix_fund_configs_id ON fund_configs (id);
CREATE INDEX IF NOT EXISTS ix_instances_id ON instances (id);
CREATE INDEX IF NOT EXISTS ix_positions_id ON positions (id);
CREATE INDEX IF NOT EXISTS ix_orders_id ON orders (id);
CREATE INDEX IF NOT EXISTS ix_position_step_locks_id ON position_step_locks (id);

-- 完成
