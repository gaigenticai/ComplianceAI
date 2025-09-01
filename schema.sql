-- Agentic AI KYC Engine - Complete Database Schema
-- Production-grade PostgreSQL schema for KYC processing system
-- This schema supports all features implemented in the system

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Customers table - Core customer information
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(100) PRIMARY KEY,
    external_customer_id VARCHAR(100) UNIQUE,
    customer_type VARCHAR(50) NOT NULL DEFAULT 'individual', -- individual, corporate
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, active, suspended, closed
    risk_level VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Indexes
    INDEX idx_customers_status (status),
    INDEX idx_customers_risk_level (risk_level),
    INDEX idx_customers_created_at (created_at),
    INDEX idx_customers_external_id (external_customer_id)
);

-- KYC Sessions table - Processing sessions
CREATE TABLE IF NOT EXISTS kyc_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed, requires_review
    current_stage VARCHAR(50) DEFAULT 'data_ingestion', -- data_ingestion, quality_validation, kyc_analysis, compliance_check, decision_making, completed
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    regulatory_requirements TEXT[], -- Array of regulatory requirements
    session_data JSONB, -- Complete session data
    processing_start_time TIMESTAMP WITH TIME ZONE,
    processing_end_time TIMESTAMP WITH TIME ZONE,
    processing_duration_seconds DECIMAL(10,3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_kyc_sessions_customer_id (customer_id),
    INDEX idx_kyc_sessions_status (status),
    INDEX idx_kyc_sessions_stage (current_stage),
    INDEX idx_kyc_sessions_created_at (created_at),
    INDEX idx_kyc_sessions_priority (priority)
);

-- KYC Results table - Final processing results
CREATE TABLE IF NOT EXISTS kyc_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL UNIQUE,
    customer_id VARCHAR(100) NOT NULL,
    decision VARCHAR(50) NOT NULL, -- approved, rejected, requires_review, requires_additional_info
    confidence_score DECIMAL(5,4) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    risk_score DECIMAL(5,4) CHECK (risk_score >= 0 AND risk_score <= 1),
    compliance_status VARCHAR(50) NOT NULL,
    processing_time DECIMAL(10,3),
    agent_results JSONB NOT NULL, -- Results from all agents
    recommendations TEXT[],
    next_review_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_kyc_results_customer_id (customer_id),
    INDEX idx_kyc_results_decision (decision),
    INDEX idx_kyc_results_confidence_score (confidence_score),
    INDEX idx_kyc_results_risk_score (risk_score),
    INDEX idx_kyc_results_completed_at (completed_at),
    INDEX idx_kyc_results_next_review (next_review_date)
);

-- =============================================================================
-- AGENT-SPECIFIC TABLES
-- =============================================================================

-- Data Ingestion Results
CREATE TABLE IF NOT EXISTS data_ingestion_results (
    ingestion_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    source_format VARCHAR(50), -- csv, json, xml, pdf, image, database
    original_data JSONB,
    normalized_data JSONB,
    schema_detected JSONB,
    extraction_metadata JSONB,
    processing_time DECIMAL(8,3),
    status VARCHAR(50) DEFAULT 'completed', -- processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_data_ingestion_session_id (session_id),
    INDEX idx_data_ingestion_customer_id (customer_id),
    INDEX idx_data_ingestion_status (status),
    INDEX idx_data_ingestion_created_at (created_at)
);

-- KYC Analysis Results
CREATE TABLE IF NOT EXISTS kyc_analysis_results (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    analysis_type VARCHAR(50) DEFAULT 'full', -- full, basic, enhanced
    risk_assessment JSONB NOT NULL,
    compliance_results JSONB,
    agent_insights JSONB,
    processing_time DECIMAL(8,3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_kyc_analysis_session_id (session_id),
    INDEX idx_kyc_analysis_customer_id (customer_id),
    INDEX idx_kyc_analysis_created_at (created_at)
);

-- Decision Making Results
CREATE TABLE IF NOT EXISTS decision_results (
    decision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    decision_type VARCHAR(50) NOT NULL, -- kyc_approval, risk_escalation, compliance_action
    final_decision VARCHAR(50) NOT NULL,
    confidence_level VARCHAR(20), -- low, medium, high, very_high
    reasoning TEXT[],
    risk_assessment JSONB,
    audit_trail JSONB,
    escalation_required BOOLEAN DEFAULT FALSE,
    next_actions TEXT[],
    processing_time DECIMAL(8,3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_decision_results_session_id (session_id),
    INDEX idx_decision_results_customer_id (customer_id),
    INDEX idx_decision_results_decision (final_decision),
    INDEX idx_decision_results_escalation (escalation_required),
    INDEX idx_decision_results_created_at (created_at)
);

-- Compliance Check Results
CREATE TABLE IF NOT EXISTS compliance_check_results (
    check_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100),
    customer_id VARCHAR(100) NOT NULL,
    regulation_types TEXT[] NOT NULL,
    overall_status VARCHAR(50) NOT NULL, -- compliant, non_compliant, requires_attention, under_review
    regulation_results JSONB NOT NULL,
    violations JSONB,
    compliance_score DECIMAL(5,4) CHECK (compliance_score >= 0 AND compliance_score <= 1),
    recommendations TEXT[],
    next_review_date TIMESTAMP WITH TIME ZONE,
    processing_time DECIMAL(8,3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_compliance_check_session_id (session_id),
    INDEX idx_compliance_check_customer_id (customer_id),
    INDEX idx_compliance_check_status (overall_status),
    INDEX idx_compliance_check_score (compliance_score),
    INDEX idx_compliance_check_created_at (created_at)
);

-- Data Quality Results
CREATE TABLE IF NOT EXISTS data_quality_results (
    quality_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100),
    customer_id VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) NOT NULL, -- personal_info, financial_data, documents, transactions
    overall_score DECIMAL(5,4) CHECK (overall_score >= 0 AND overall_score <= 1),
    quality_scores JSONB, -- completeness, accuracy, consistency, validity, uniqueness
    validation_status VARCHAR(50), -- passed, failed, warning, skipped
    issues_found JSONB,
    anomalies JSONB,
    recommendations TEXT[],
    processing_time DECIMAL(8,3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_data_quality_session_id (session_id),
    INDEX idx_data_quality_customer_id (customer_id),
    INDEX idx_data_quality_score (overall_score),
    INDEX idx_data_quality_status (validation_status),
    INDEX idx_data_quality_created_at (created_at)
);

-- =============================================================================
-- COMPLIANCE AND REGULATORY TABLES
-- =============================================================================

-- Compliance Violations
CREATE TABLE IF NOT EXISTS compliance_violations (
    violation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    regulation_type VARCHAR(50) NOT NULL, -- aml, gdpr, basel_iii, pci_dss, sox
    violation_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- low, medium, high, critical
    description TEXT NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    auto_resolved BOOLEAN DEFAULT FALSE,
    escalated BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    
    -- Foreign keys
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_compliance_violations_customer_id (customer_id),
    INDEX idx_compliance_violations_regulation (regulation_type),
    INDEX idx_compliance_violations_severity (severity),
    INDEX idx_compliance_violations_detected_at (detected_at),
    INDEX idx_compliance_violations_resolved (resolved_at),
    INDEX idx_compliance_violations_escalated (escalated)
);

-- Sanctions Screening Results
CREATE TABLE IF NOT EXISTS sanctions_screening (
    screening_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    screening_type VARCHAR(50) NOT NULL, -- ofac, un_sanctions, eu_sanctions, pep, adverse_media
    screening_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    match_found BOOLEAN DEFAULT FALSE,
    matches JSONB,
    confidence_score DECIMAL(5,4),
    risk_level VARCHAR(20), -- low, medium, high, critical
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_sanctions_screening_customer_id (customer_id),
    INDEX idx_sanctions_screening_type (screening_type),
    INDEX idx_sanctions_screening_match (match_found),
    INDEX idx_sanctions_screening_date (screening_date),
    INDEX idx_sanctions_screening_risk (risk_level)
);

-- =============================================================================
-- AUDIT AND MONITORING TABLES
-- =============================================================================

-- Audit Trail
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
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE SET NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_audit_trail_session_id (session_id),
    INDEX idx_audit_trail_customer_id (customer_id),
    INDEX idx_audit_trail_agent (agent_name),
    INDEX idx_audit_trail_action (action),
    INDEX idx_audit_trail_timestamp (timestamp),
    INDEX idx_audit_trail_user_id (user_id)
);

-- System Metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,6),
    metric_type VARCHAR(50), -- counter, gauge, histogram
    labels JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_system_metrics_name (metric_name),
    INDEX idx_system_metrics_timestamp (timestamp),
    INDEX idx_system_metrics_type (metric_type)
);

-- Agent Health Status
CREATE TABLE IF NOT EXISTS agent_health (
    health_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL, -- healthy, unhealthy, warning
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    error_rate DECIMAL(5,4),
    processed_requests BIGINT DEFAULT 0,
    metadata JSONB,
    
    -- Indexes
    INDEX idx_agent_health_name (agent_name),
    INDEX idx_agent_health_status (status),
    INDEX idx_agent_health_heartbeat (last_heartbeat)
);

-- =============================================================================
-- CONFIGURATION TABLES
-- =============================================================================

-- System Configuration
CREATE TABLE IF NOT EXISTS system_config (
    config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(200) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    config_type VARCHAR(50) DEFAULT 'application', -- application, agent, regulatory, security
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    
    -- Indexes
    INDEX idx_system_config_key (config_key),
    INDEX idx_system_config_type (config_type),
    INDEX idx_system_config_updated_at (updated_at)
);

-- Regulatory Rules
CREATE TABLE IF NOT EXISTS regulatory_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regulation_type VARCHAR(50) NOT NULL, -- aml, gdpr, basel_iii, etc.
    rule_name VARCHAR(200) NOT NULL,
    rule_definition JSONB NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    is_active BOOLEAN DEFAULT TRUE,
    jurisdiction VARCHAR(10), -- US, EU, UK, etc.
    effective_date DATE,
    expiry_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_regulatory_rules_type (regulation_type),
    INDEX idx_regulatory_rules_active (is_active),
    INDEX idx_regulatory_rules_jurisdiction (jurisdiction),
    INDEX idx_regulatory_rules_effective (effective_date),
    UNIQUE INDEX idx_regulatory_rules_unique (regulation_type, rule_name, jurisdiction)
);

-- =============================================================================
-- PERFORMANCE OPTIMIZATION TABLES
-- =============================================================================

-- Processing Queue
CREATE TABLE IF NOT EXISTS processing_queue (
    queue_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 5, -- 1 (highest) to 10 (lowest)
    queue_status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    assigned_agent VARCHAR(100),
    queued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_processing_queue_status (queue_status),
    INDEX idx_processing_queue_priority (priority),
    INDEX idx_processing_queue_queued_at (queued_at),
    INDEX idx_processing_queue_agent (assigned_agent)
);

-- =============================================================================
-- VIEWS FOR REPORTING AND ANALYTICS
-- =============================================================================

-- KYC Processing Summary View
CREATE OR REPLACE VIEW kyc_processing_summary AS
SELECT 
    ks.session_id,
    ks.customer_id,
    ks.status,
    ks.current_stage,
    ks.priority,
    ks.created_at,
    ks.processing_duration_seconds,
    kr.decision,
    kr.confidence_score,
    kr.risk_score,
    kr.compliance_status,
    CASE 
        WHEN ks.status = 'completed' THEN 'success'
        WHEN ks.status = 'failed' THEN 'failure'
        ELSE 'in_progress'
    END as outcome
FROM kyc_sessions ks
LEFT JOIN kyc_results kr ON ks.session_id = kr.session_id;

-- Daily Processing Statistics View
CREATE OR REPLACE VIEW daily_processing_stats AS
SELECT 
    DATE(created_at) as processing_date,
    COUNT(*) as total_sessions,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_sessions,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_sessions,
    AVG(processing_duration_seconds) as avg_processing_time,
    MIN(processing_duration_seconds) as min_processing_time,
    MAX(processing_duration_seconds) as max_processing_time
FROM kyc_sessions
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY processing_date DESC;

-- Compliance Violations Summary View
CREATE OR REPLACE VIEW compliance_violations_summary AS
SELECT 
    regulation_type,
    severity,
    COUNT(*) as violation_count,
    COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) as resolved_count,
    COUNT(CASE WHEN escalated = TRUE THEN 1 END) as escalated_count,
    AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, CURRENT_TIMESTAMP) - detected_at))/3600) as avg_resolution_hours
FROM compliance_violations
WHERE detected_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY regulation_type, severity
ORDER BY regulation_type, severity;

-- =============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- =============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers to relevant tables
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kyc_sessions_updated_at BEFORE UPDATE ON kyc_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_regulatory_rules_updated_at BEFORE UPDATE ON regulatory_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- INITIAL DATA SETUP
-- =============================================================================

-- Insert default system configuration
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('system.version', '"1.0.0"', 'application', 'System version'),
('system.maintenance_mode', 'false', 'application', 'System maintenance mode flag'),
('processing.max_concurrent_sessions', '100', 'application', 'Maximum concurrent processing sessions'),
('processing.session_timeout_seconds', '3600', 'application', 'Session timeout in seconds'),
('agents.health_check_interval', '30', 'agent', 'Agent health check interval in seconds'),
('compliance.default_regulations', '["aml", "gdpr"]', 'regulatory', 'Default regulatory requirements'),
('security.session_timeout_minutes', '60', 'security', 'Security session timeout in minutes'),
('security.max_login_attempts', '5', 'security', 'Maximum login attempts before lockout')
ON CONFLICT (config_key) DO NOTHING;

-- Insert default regulatory rules
INSERT INTO regulatory_rules (regulation_type, rule_name, rule_definition, severity, jurisdiction) VALUES
('aml', 'sanctions_screening', '{"required": true, "lists": ["ofac", "un", "eu"], "match_threshold": 0.8}', 'critical', 'US'),
('aml', 'pep_screening', '{"required": true, "sources": ["world_check", "dow_jones"], "match_threshold": 0.7}', 'high', 'US'),
('aml', 'transaction_monitoring', '{"enabled": true, "thresholds": {"structuring": 10000, "velocity": 50}}', 'high', 'US'),
('gdpr', 'consent_management', '{"required": true, "explicit_consent": true, "consent_expiry_days": 365}', 'high', 'EU'),
('gdpr', 'data_minimization', '{"enabled": true, "max_fields": 50, "purpose_limitation": true}', 'medium', 'EU'),
('gdpr', 'data_retention', '{"max_retention_days": 2555, "auto_deletion": true}', 'high', 'EU'),
('basel_iii', 'operational_risk', '{"assessment_required": true, "risk_threshold": 0.7}', 'medium', 'US'),
('basel_iii', 'model_validation', '{"required": true, "validation_frequency": "quarterly"}', 'medium', 'US')
ON CONFLICT (regulation_type, rule_name, jurisdiction) DO NOTHING;

-- =============================================================================
-- PERFORMANCE INDEXES AND OPTIMIZATIONS
-- =============================================================================

-- Additional performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kyc_sessions_composite 
ON kyc_sessions (customer_id, status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kyc_results_composite 
ON kyc_results (customer_id, decision, completed_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_violations_composite 
ON compliance_violations (customer_id, regulation_type, severity, detected_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_trail_composite 
ON audit_trail (customer_id, agent_name, timestamp DESC);

-- Partial indexes for active records
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kyc_sessions_active 
ON kyc_sessions (session_id, current_stage) 
WHERE status IN ('pending', 'processing');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_violations_unresolved 
ON compliance_violations (violation_id, severity, detected_at) 
WHERE resolved_at IS NULL;

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE customers IS 'Core customer information and status';
COMMENT ON TABLE kyc_sessions IS 'KYC processing sessions with status tracking';
COMMENT ON TABLE kyc_results IS 'Final KYC processing results and decisions';
COMMENT ON TABLE data_ingestion_results IS 'Results from data ingestion agent processing';
COMMENT ON TABLE kyc_analysis_results IS 'Results from KYC analysis agent processing';
COMMENT ON TABLE decision_results IS 'Results from decision making agent processing';
COMMENT ON TABLE compliance_check_results IS 'Results from compliance monitoring agent';
COMMENT ON TABLE data_quality_results IS 'Results from data quality agent validation';
COMMENT ON TABLE compliance_violations IS 'Regulatory compliance violations tracking';
COMMENT ON TABLE sanctions_screening IS 'Sanctions and watchlist screening results';
COMMENT ON TABLE audit_trail IS 'Complete audit trail for all system actions';
COMMENT ON TABLE system_metrics IS 'System performance and operational metrics';
COMMENT ON TABLE agent_health IS 'Health status monitoring for all AI agents';
COMMENT ON TABLE system_config IS 'System configuration parameters';
COMMENT ON TABLE regulatory_rules IS 'Regulatory compliance rules and definitions';
COMMENT ON TABLE processing_queue IS 'Processing queue for managing workload';

-- =============================================================================
-- AGENTIC AI ADVANCED FEATURES - NEW TABLES
-- =============================================================================

-- Compliance Rules table - Dynamic compliance rule storage (Pillar 3)
CREATE TABLE IF NOT EXISTS compliance_rules (
    rule_id VARCHAR(200) PRIMARY KEY,
    region VARCHAR(100) NOT NULL,
    regulation_type VARCHAR(50) NOT NULL, -- AML, KYC, GDPR, etc.
    rule_title VARCHAR(500) NOT NULL,
    rule_content TEXT NOT NULL,
    effective_date DATE,
    expiry_date DATE,
    source_url TEXT,
    confidence_score DECIMAL(3,2) DEFAULT 0.5, -- 0.0 to 1.0
    discovered_via_web BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for efficient querying
    INDEX idx_compliance_rules_region (region),
    INDEX idx_compliance_rules_type (regulation_type),
    INDEX idx_compliance_rules_region_type (region, regulation_type),
    INDEX idx_compliance_rules_confidence (confidence_score DESC),
    INDEX idx_compliance_rules_updated (last_updated DESC)
);

-- AI Memory Storage table - Case summaries and learning patterns (Pillar 2)
-- Note: This table is for metadata only. Vector embeddings are stored in Qdrant/Pinecone
CREATE TABLE IF NOT EXISTS ai_memory_metadata (
    memory_id VARCHAR(200) PRIMARY KEY,
    memory_type VARCHAR(50) NOT NULL, -- case_summary, compliance_rule, document_analysis, decision_pattern, agent_learning
    agent_name VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100),
    session_id VARCHAR(100),
    content_summary TEXT, -- Brief summary of the stored content
    tags TEXT[], -- Array of tags for categorization
    confidence_score DECIMAL(3,2) DEFAULT 1.0,
    vector_backend VARCHAR(20) DEFAULT 'qdrant', -- qdrant, pinecone
    vector_id VARCHAR(200), -- ID in the vector database
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    
    -- Foreign key relationships
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE SET NULL,
    
    -- Indexes for efficient retrieval
    INDEX idx_ai_memory_type (memory_type),
    INDEX idx_ai_memory_agent (agent_name),
    INDEX idx_ai_memory_customer (customer_id),
    INDEX idx_ai_memory_session (session_id),
    INDEX idx_ai_memory_created (created_at DESC),
    INDEX idx_ai_memory_accessed (last_accessed DESC),
    INDEX idx_ai_memory_tags USING GIN (tags),
    INDEX idx_ai_memory_composite (memory_type, agent_name, created_at DESC)
);

-- Document Analysis Results table - Visual document processing results (Pillar 1)
CREATE TABLE IF NOT EXISTS document_analysis_results (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    document_path TEXT NOT NULL,
    document_type VARCHAR(100), -- passport, driver_license, utility_bill, etc.
    vision_model VARCHAR(50) NOT NULL, -- gpt4v, llava
    analysis_result JSONB NOT NULL, -- Complete analysis results
    extracted_data JSONB, -- Structured extracted data
    confidence_score DECIMAL(3,2),
    processing_time_seconds DECIMAL(8,3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key relationships
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_document_analysis_session (session_id),
    INDEX idx_document_analysis_customer (customer_id),
    INDEX idx_document_analysis_type (document_type),
    INDEX idx_document_analysis_model (vision_model),
    INDEX idx_document_analysis_confidence (confidence_score DESC),
    INDEX idx_document_analysis_created (created_at DESC)
);

-- Web Search History table - Track autonomous web searches for compliance rules
CREATE TABLE IF NOT EXISTS web_search_history (
    search_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    search_query TEXT NOT NULL,
    region VARCHAR(100) NOT NULL,
    regulation_types TEXT[], -- Array of regulation types searched
    search_engine VARCHAR(50) DEFAULT 'tavily', -- tavily, duckduckgo, fallback
    results_count INTEGER DEFAULT 0,
    rules_discovered INTEGER DEFAULT 0,
    search_duration_seconds DECIMAL(6,3),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_web_search_region (region),
    INDEX idx_web_search_created (created_at DESC),
    INDEX idx_web_search_success (success),
    INDEX idx_web_search_query_text USING GIN (to_tsvector('english', search_query))
);

-- Agent Performance Metrics table - Enhanced metrics for new capabilities
CREATE TABLE IF NOT EXISTS agent_performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- vision_processing, memory_retrieval, rule_discovery, etc.
    metric_value DECIMAL(10,4) NOT NULL,
    metric_unit VARCHAR(20), -- seconds, count, percentage, etc.
    session_id VARCHAR(100),
    customer_id VARCHAR(100),
    additional_data JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key relationships
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES kyc_sessions(session_id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_agent_metrics_agent (agent_name),
    INDEX idx_agent_metrics_type (metric_type),
    INDEX idx_agent_metrics_recorded (recorded_at DESC),
    INDEX idx_agent_metrics_composite (agent_name, metric_type, recorded_at DESC)
);

-- =============================================================================
-- ADDITIONAL INDEXES FOR ADVANCED FEATURES
-- =============================================================================

-- Composite indexes for complex queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_rules_region_confidence
ON compliance_rules (region, confidence_score DESC, last_updated DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_memory_customer_type
ON ai_memory_metadata (customer_id, memory_type, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_document_analysis_customer_type
ON document_analysis_results (customer_id, document_type, created_at DESC);

-- Full-text search indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_rules_content_search
ON compliance_rules USING GIN (to_tsvector('english', rule_title || ' ' || rule_content));

-- =============================================================================
-- COMMENTS FOR NEW TABLES
-- =============================================================================

COMMENT ON TABLE compliance_rules IS 'Dynamic compliance rules discovered via web search and local storage';
COMMENT ON TABLE ai_memory_metadata IS 'Metadata for AI memory entries stored in vector databases';
COMMENT ON TABLE document_analysis_results IS 'Results from visual document analysis using AI vision models';
COMMENT ON TABLE web_search_history IS 'History of autonomous web searches for compliance rules';
COMMENT ON TABLE agent_performance_metrics IS 'Enhanced performance metrics for advanced agent capabilities';

-- Schema version tracking
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('schema.version', '"2.0.0"', 'application', 'Database schema version with agentic AI features')
ON CONFLICT (config_key) DO UPDATE SET 
config_value = '"2.0.0"', 
updated_at = CURRENT_TIMESTAMP;

-- Insert advanced feature flags
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('features.vision_processing', 'true', 'feature', 'Enable multimodal document understanding'),
('features.ai_memory', 'true', 'feature', 'Enable long-term AI memory and learning'),
('features.autonomous_rules', 'true', 'feature', 'Enable autonomous compliance rule discovery'),
('features.web_search', 'true', 'feature', 'Enable web search for compliance rules')
ON CONFLICT (config_key) DO NOTHING;

-- =============================================================================
-- REVAMP: SIMPLIFIED 3-AGENT ARCHITECTURE TABLES
-- =============================================================================

-- Intake & Processing Agent Results (Combines Data Ingestion + Data Quality)
CREATE TABLE IF NOT EXISTS intake_processing_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    document_id VARCHAR(100) NOT NULL,
    extracted_data JSONB NOT NULL,
    confidence DECIMAL(5,4) CHECK (confidence >= 0 AND confidence <= 1),
    processing_method VARCHAR(50) NOT NULL, -- local_ocr, ai_vision, failed
    quality_score DECIMAL(5,4) CHECK (quality_score >= 0 AND quality_score <= 1),
    anomalies_detected TEXT[],
    processing_time_seconds DECIMAL(10,3),
    estimated_cost_dollars DECIMAL(10,4),
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for intake_processing_results
CREATE INDEX IF NOT EXISTS idx_intake_session_id ON intake_processing_results (session_id);
CREATE INDEX IF NOT EXISTS idx_intake_document_id ON intake_processing_results (document_id);
CREATE INDEX IF NOT EXISTS idx_intake_processing_method ON intake_processing_results (processing_method);
CREATE INDEX IF NOT EXISTS idx_intake_confidence ON intake_processing_results (confidence);
CREATE INDEX IF NOT EXISTS idx_intake_quality_score ON intake_processing_results (quality_score);
CREATE INDEX IF NOT EXISTS idx_intake_created_at ON intake_processing_results (created_at);

-- Intelligence & Compliance Agent Results (Combines KYC Analysis + Compliance Monitoring)
CREATE TABLE IF NOT EXISTS intelligence_compliance_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    risk_assessment JSONB NOT NULL,
    compliance_checks JSONB NOT NULL,
    sanctions_screening JSONB NOT NULL,
    pep_screening JSONB NOT NULL,
    overall_recommendation VARCHAR(100) NOT NULL,
    processing_time_seconds DECIMAL(10,3),
    estimated_cost_dollars DECIMAL(10,4),
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Indexes for intelligence_compliance_results
CREATE INDEX IF NOT EXISTS idx_intelligence_session_id ON intelligence_compliance_results (session_id);
CREATE INDEX IF NOT EXISTS idx_intelligence_customer_id ON intelligence_compliance_results (customer_id);
CREATE INDEX IF NOT EXISTS idx_intelligence_recommendation ON intelligence_compliance_results (overall_recommendation);
CREATE INDEX IF NOT EXISTS idx_intelligence_created_at ON intelligence_compliance_results (created_at);

-- Decision & Orchestration Agent Results (Enhanced with Cost Optimization)
CREATE TABLE IF NOT EXISTS decision_orchestration_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    decision VARCHAR(50) NOT NULL, -- approve, reject, manual_review, escalate
    confidence DECIMAL(5,4) CHECK (confidence >= 0 AND confidence <= 1),
    reasoning TEXT NOT NULL,
    processing_method VARCHAR(50) NOT NULL, -- fast_track, standard, complex_llm
    risk_assessment JSONB NOT NULL,
    compliance_summary JSONB NOT NULL,
    escalation_required BOOLEAN DEFAULT FALSE,
    human_review_required BOOLEAN DEFAULT FALSE,
    processing_time_seconds DECIMAL(10,3),
    estimated_cost_dollars DECIMAL(10,4),
    audit_trail JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Indexes for decision_orchestration_results
CREATE INDEX IF NOT EXISTS idx_decision_session_id ON decision_orchestration_results (session_id);
CREATE INDEX IF NOT EXISTS idx_decision_customer_id ON decision_orchestration_results (customer_id);
CREATE INDEX IF NOT EXISTS idx_decision_decision ON decision_orchestration_results (decision);
CREATE INDEX IF NOT EXISTS idx_decision_processing_method ON decision_orchestration_results (processing_method);
CREATE INDEX IF NOT EXISTS idx_decision_escalation ON decision_orchestration_results (escalation_required);
CREATE INDEX IF NOT EXISTS idx_decision_human_review ON decision_orchestration_results (human_review_required);
CREATE INDEX IF NOT EXISTS idx_decision_created_at ON decision_orchestration_results (created_at);

-- Cost Optimization Metrics Table
CREATE TABLE IF NOT EXISTS cost_optimization_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(50) NOT NULL, -- intake_processing, intelligence_compliance, decision_orchestration
    processing_method VARCHAR(50) NOT NULL,
    cost_dollars DECIMAL(10,4) NOT NULL,
    processing_time_seconds DECIMAL(10,3) NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for cost_optimization_metrics
CREATE INDEX IF NOT EXISTS idx_cost_metrics_session_id ON cost_optimization_metrics (session_id);
CREATE INDEX IF NOT EXISTS idx_cost_metrics_agent ON cost_optimization_metrics (agent_name);
CREATE INDEX IF NOT EXISTS idx_cost_metrics_method ON cost_optimization_metrics (processing_method);
CREATE INDEX IF NOT EXISTS idx_cost_metrics_cost ON cost_optimization_metrics (cost_dollars);
CREATE INDEX IF NOT EXISTS idx_cost_metrics_created_at ON cost_optimization_metrics (created_at);

-- Performance Benchmarks Table
CREATE TABLE IF NOT EXISTS performance_benchmarks (
    benchmark_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_date DATE NOT NULL,
    architecture_version VARCHAR(50) NOT NULL, -- 5-agent, 3-agent-simplified
    total_cases_processed INTEGER NOT NULL,
    average_processing_time_seconds DECIMAL(10,3) NOT NULL,
    average_cost_per_case_dollars DECIMAL(10,4) NOT NULL,
    fast_track_percentage DECIMAL(5,2) NOT NULL,
    accuracy_percentage DECIMAL(5,2) NOT NULL,
    throughput_cases_per_hour INTEGER NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance_benchmarks
CREATE INDEX IF NOT EXISTS idx_benchmarks_test_date ON performance_benchmarks (test_date);
CREATE INDEX IF NOT EXISTS idx_benchmarks_architecture ON performance_benchmarks (architecture_version);
CREATE INDEX IF NOT EXISTS idx_benchmarks_cost ON performance_benchmarks (average_cost_per_case_dollars);
CREATE INDEX IF NOT EXISTS idx_benchmarks_throughput ON performance_benchmarks (throughput_cases_per_hour);

-- Comments for new simplified architecture tables
COMMENT ON TABLE intake_processing_results IS 'Results from Intake & Processing Agent (combines data ingestion and quality assessment)';
COMMENT ON TABLE intelligence_compliance_results IS 'Results from Intelligence & Compliance Agent (combines KYC analysis and compliance monitoring)';
COMMENT ON TABLE decision_orchestration_results IS 'Results from Decision & Orchestration Agent (enhanced with cost optimization)';
COMMENT ON TABLE cost_optimization_metrics IS 'Metrics for tracking cost optimization across the simplified 3-agent architecture';
COMMENT ON TABLE performance_benchmarks IS 'Performance benchmarks comparing 5-agent vs 3-agent simplified architecture';

-- Update schema version for simplified architecture
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('schema.version', '"3.0.0"', 'application', 'Database schema version with simplified 3-agent architecture')
ON CONFLICT (config_key) DO UPDATE SET 
config_value = '"3.0.0"', 
updated_at = CURRENT_TIMESTAMP;

-- Insert simplified architecture feature flags
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('architecture.simplified', 'true', 'feature', 'Enable simplified 3-agent architecture'),
('cost_optimization.enabled', 'true', 'feature', 'Enable cost optimization features'),
('cost_optimization.target_per_case', '0.50', 'setting', 'Target cost per KYC case in USD'),
('processing.fast_track_percentage', '80', 'setting', 'Target percentage of cases for fast-track processing')
ON CONFLICT (config_key) DO NOTHING;

-- =============================================================================
-- REVAMPED AGENT TABLES (Added for Rule 5 compliance)
-- =============================================================================

-- Agent performance metrics for the 3-agent architecture
CREATE TABLE IF NOT EXISTS agent_performance_metrics (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL, -- 'intake', 'intelligence', 'decision'
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    metric_unit VARCHAR(50),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    case_id UUID REFERENCES cases(id),
    
    CONSTRAINT unique_agent_metric_case UNIQUE(agent_name, metric_name, case_id, recorded_at)
);

-- Agent communication logs for debugging and monitoring
CREATE TABLE IF NOT EXISTS agent_communications (
    id SERIAL PRIMARY KEY,
    from_agent VARCHAR(100) NOT NULL,
    to_agent VARCHAR(100) NOT NULL,
    message_type VARCHAR(50) NOT NULL, -- 'request', 'response', 'notification'
    message_content JSONB NOT NULL,
    case_id UUID REFERENCES cases(id),
    correlation_id UUID NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    received_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'sent' -- 'sent', 'received', 'processed', 'failed'
);

-- Cost tracking for the simplified architecture
CREATE TABLE IF NOT EXISTS cost_tracking (
    id SERIAL PRIMARY KEY,
    case_id UUID REFERENCES cases(id),
    agent_name VARCHAR(100) NOT NULL,
    operation_type VARCHAR(100) NOT NULL, -- 'ocr', 'ai_vision', 'llm_analysis', 'decision'
    cost_usd DECIMAL(10,6) NOT NULL,
    processing_time_ms INTEGER,
    tokens_used INTEGER,
    model_used VARCHAR(100),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_performance_agent_name ON agent_performance_metrics(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_performance_recorded_at ON agent_performance_metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_agent_communications_case_id ON agent_communications(case_id);
CREATE INDEX IF NOT EXISTS idx_agent_communications_correlation_id ON agent_communications(correlation_id);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_case_id ON cost_tracking(case_id);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_agent_name ON cost_tracking(agent_name);

-- End of schema
