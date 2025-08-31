-- PostgreSQL Database Initialization Script
-- This script sets up the initial database structure and data

-- Create the main database if it doesn't exist
-- Note: This runs as part of docker-entrypoint-initdb.d

-- Set up extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create application user with proper permissions
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'kyc_app') THEN
        CREATE ROLE kyc_app WITH LOGIN PASSWORD 'kyc_app_password';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE kyc_db TO kyc_app;
GRANT USAGE ON SCHEMA public TO kyc_app;
GRANT CREATE ON SCHEMA public TO kyc_app;

-- Create tables (from schema.sql)
-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(100) PRIMARY KEY,
    external_customer_id VARCHAR(100) UNIQUE,
    customer_type VARCHAR(50) NOT NULL DEFAULT 'individual',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    risk_level VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- KYC Sessions table
CREATE TABLE IF NOT EXISTS kyc_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    current_stage VARCHAR(50) DEFAULT 'data_ingestion',
    priority VARCHAR(20) DEFAULT 'normal',
    regulatory_requirements TEXT[],
    session_data JSONB,
    processing_start_time TIMESTAMP WITH TIME ZONE,
    processing_end_time TIMESTAMP WITH TIME ZONE,
    processing_duration_seconds DECIMAL(10,3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- KYC Results table
CREATE TABLE IF NOT EXISTS kyc_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL UNIQUE,
    customer_id VARCHAR(100) NOT NULL,
    decision VARCHAR(50) NOT NULL,
    confidence_score DECIMAL(5,4) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    risk_score DECIMAL(5,4) CHECK (risk_score >= 0 AND risk_score <= 1),
    compliance_status VARCHAR(50) NOT NULL,
    processing_time DECIMAL(10,3),
    agent_results JSONB NOT NULL,
    recommendations TEXT[],
    next_review_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- System Configuration table
CREATE TABLE IF NOT EXISTS system_config (
    config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(200) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    config_type VARCHAR(50) DEFAULT 'application',
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- Audit Trail table
CREATE TABLE IF NOT EXISTS audit_trail (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100),
    customer_id VARCHAR(100),
    agent_name VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    user_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE SET NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE SET NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
CREATE INDEX IF NOT EXISTS idx_customers_risk_level ON customers(risk_level);
CREATE INDEX IF NOT EXISTS idx_kyc_sessions_customer_id ON kyc_sessions(customer_id);
CREATE INDEX IF NOT EXISTS idx_kyc_sessions_status ON kyc_sessions(status);
CREATE INDEX IF NOT EXISTS idx_kyc_results_customer_id ON kyc_results(customer_id);
CREATE INDEX IF NOT EXISTS idx_kyc_results_decision ON kyc_results(decision);
CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trail(timestamp);

-- Insert initial system configuration
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('system.version', '"1.0.0"', 'application', 'System version'),
('system.maintenance_mode', 'false', 'application', 'System maintenance mode flag'),
('processing.max_concurrent_sessions', '100', 'application', 'Maximum concurrent processing sessions'),
('agents.health_check_interval', '30', 'agent', 'Agent health check interval in seconds'),
('compliance.default_regulations', '["aml", "gdpr"]', 'regulatory', 'Default regulatory requirements')
ON CONFLICT (config_key) DO NOTHING;

-- Grant permissions on all tables to application user
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO kyc_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO kyc_app;

-- Create update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kyc_sessions_updated_at BEFORE UPDATE ON kyc_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Log initialization completion
INSERT INTO audit_trail (action, details, timestamp) VALUES 
('database_initialized', '{"message": "Database initialization completed successfully"}', CURRENT_TIMESTAMP);
