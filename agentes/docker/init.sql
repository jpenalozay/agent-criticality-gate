-- Initialize database schema

CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(255) PRIMARY KEY,
    requirement TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    total_time_ms INTEGER,
    result JSONB
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);

CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255),
    timestamp TIMESTAMP NOT NULL,
    actor VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    details JSONB,
    checksum VARCHAR(64) NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX idx_audit_task_id ON audit_events(task_id);
CREATE INDEX idx_audit_timestamp ON audit_events(timestamp);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
