-- Initial migration for KYC Orchestrator
-- This creates the basic tables needed for the orchestrator

CREATE TABLE IF NOT EXISTS kyc_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    customer_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    health BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_kyc_sessions_session_id ON kyc_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_kyc_sessions_customer_id ON kyc_sessions(customer_id);
CREATE INDEX IF NOT EXISTS idx_agent_status_name ON agent_status(agent_name);