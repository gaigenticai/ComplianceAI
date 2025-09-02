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

-- =============================================================================
-- ENHANCED UI FEATURES TABLES (Added for 3-Agent System v3.0.0)
-- =============================================================================

-- Table for storing compliance rules created via UI
CREATE TABLE IF NOT EXISTS compliance_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(100) NOT NULL, -- AML, KYC, GDPR, Basel III, FATCA, CRS
    description TEXT NOT NULL,
    priority INTEGER NOT NULL CHECK (priority >= 1 AND priority <= 10),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    CONSTRAINT unique_rule_name UNIQUE (rule_name)
);

-- Table for storing test results from the testing dashboard
CREATE TABLE IF NOT EXISTS test_results (
    test_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_type VARCHAR(50) NOT NULL, -- health, performance, integration
    agent_name VARCHAR(100) NOT NULL, -- intake, intelligence, decision
    result JSONB NOT NULL, -- Store complete test result data
    test_passed BOOLEAN NOT NULL,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_test_type CHECK (test_type IN ('health', 'performance', 'integration')),
    CONSTRAINT valid_agent_name CHECK (agent_name IN ('intake', 'intelligence', 'decision'))
);

-- Table for storing system performance metrics for the performance dashboard
CREATE TABLE IF NOT EXISTS system_performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_type VARCHAR(100) NOT NULL, -- processing_time, success_rate, cost_per_case, etc.
    metric_value DECIMAL(10,4) NOT NULL,
    metric_unit VARCHAR(50), -- seconds, percentage, dollars, etc.
    agent_name VARCHAR(100), -- NULL for system-wide metrics
    time_period VARCHAR(50), -- hourly, daily, weekly
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB -- Additional metric metadata
);

-- Table for storing user guide access logs (for analytics)
CREATE TABLE IF NOT EXISTS user_guide_access (
    access_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guide_section VARCHAR(100) NOT NULL, -- getting-started, kyc-processing, etc.
    user_ip VARCHAR(45),
    user_agent TEXT,
    access_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_duration INTEGER -- in seconds
);

-- Table for storing web interface sessions and user interactions
CREATE TABLE IF NOT EXISTS web_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_token VARCHAR(255) UNIQUE NOT NULL,
    user_ip VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    session_data JSONB -- Store session-specific data
);

-- Table for storing API usage statistics for monitoring
CREATE TABLE IF NOT EXISTS api_usage_stats (
    usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL, -- GET, POST, PUT, DELETE
    response_status INTEGER NOT NULL,
    response_time_ms INTEGER NOT NULL,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    user_ip VARCHAR(45),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT -- For failed requests
);

-- =============================================================================
-- INDEXES FOR ENHANCED FEATURES
-- =============================================================================

-- Compliance rules indexes
CREATE INDEX IF NOT EXISTS idx_compliance_rules_type ON compliance_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_compliance_rules_priority ON compliance_rules(priority);
CREATE INDEX IF NOT EXISTS idx_compliance_rules_active ON compliance_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_compliance_rules_created_at ON compliance_rules(created_at);

-- Test results indexes
CREATE INDEX IF NOT EXISTS idx_test_results_agent_name ON test_results(agent_name);
CREATE INDEX IF NOT EXISTS idx_test_results_test_type ON test_results(test_type);
CREATE INDEX IF NOT EXISTS idx_test_results_created_at ON test_results(created_at);
CREATE INDEX IF NOT EXISTS idx_test_results_passed ON test_results(test_passed);

-- System performance metrics indexes
CREATE INDEX IF NOT EXISTS idx_system_performance_type ON system_performance_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_system_performance_agent ON system_performance_metrics(agent_name);
CREATE INDEX IF NOT EXISTS idx_system_performance_recorded_at ON system_performance_metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_system_performance_period ON system_performance_metrics(time_period);

-- User guide access indexes
CREATE INDEX IF NOT EXISTS idx_user_guide_section ON user_guide_access(guide_section);
CREATE INDEX IF NOT EXISTS idx_user_guide_access_time ON user_guide_access(access_time);

-- Web sessions indexes
CREATE INDEX IF NOT EXISTS idx_web_sessions_token ON web_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_web_sessions_active ON web_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_web_sessions_last_activity ON web_sessions(last_activity);

-- API usage stats indexes
CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage_stats(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage_stats(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_usage_status ON api_usage_stats(response_status);
CREATE INDEX IF NOT EXISTS idx_api_usage_response_time ON api_usage_stats(response_time_ms);

-- =============================================================================
-- TRIGGERS FOR ENHANCED FEATURES
-- =============================================================================

-- Update trigger for compliance_rules
CREATE OR REPLACE FUNCTION update_compliance_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_compliance_rules_updated_at
    BEFORE UPDATE ON compliance_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_compliance_rules_updated_at();

-- Update trigger for web_sessions last_activity
CREATE OR REPLACE FUNCTION update_web_sessions_last_activity()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_activity = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_web_sessions_last_activity
    BEFORE UPDATE ON web_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_web_sessions_last_activity();

-- =============================================================================
-- VIEWS FOR ENHANCED REPORTING
-- =============================================================================

-- View for compliance rules summary
CREATE OR REPLACE VIEW compliance_rules_summary AS
SELECT 
    rule_type,
    COUNT(*) as total_rules,
    COUNT(CASE WHEN is_active THEN 1 END) as active_rules,
    AVG(priority) as avg_priority,
    MAX(created_at) as latest_rule_created
FROM compliance_rules
GROUP BY rule_type;

-- View for agent test results summary
CREATE OR REPLACE VIEW agent_test_summary AS
SELECT 
    agent_name,
    test_type,
    COUNT(*) as total_tests,
    COUNT(CASE WHEN test_passed THEN 1 END) as passed_tests,
    ROUND(COUNT(CASE WHEN test_passed THEN 1 END) * 100.0 / COUNT(*), 2) as success_rate,
    AVG(execution_time_ms) as avg_execution_time_ms,
    MAX(created_at) as last_test_run
FROM test_results
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY agent_name, test_type;

-- View for system performance overview
CREATE OR REPLACE VIEW system_performance_overview AS
SELECT 
    metric_type,
    agent_name,
    AVG(metric_value) as avg_value,
    MIN(metric_value) as min_value,
    MAX(metric_value) as max_value,
    COUNT(*) as measurement_count,
    metric_unit
FROM system_performance_metrics
WHERE recorded_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY metric_type, agent_name, metric_unit;

-- View for API usage analytics
CREATE OR REPLACE VIEW api_usage_analytics AS
SELECT 
    endpoint,
    method,
    COUNT(*) as request_count,
    AVG(response_time_ms) as avg_response_time_ms,
    COUNT(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 END) as success_count,
    COUNT(CASE WHEN response_status >= 400 THEN 1 END) as error_count,
    ROUND(COUNT(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 END) * 100.0 / COUNT(*), 2) as success_rate
FROM api_usage_stats
WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY endpoint, method
ORDER BY request_count DESC;

-- =============================================================================
-- UI REDESIGN TABLES (Added for Professional UI System v3.1.0)
-- =============================================================================

-- Table for storing UI theme configurations and customizations
CREATE TABLE IF NOT EXISTS ui_themes (
    theme_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    theme_name VARCHAR(100) NOT NULL UNIQUE,
    theme_config JSONB NOT NULL, -- Stores complete theme configuration
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    CONSTRAINT valid_theme_config CHECK (jsonb_typeof(theme_config) = 'object')
);

-- Table for tracking UI component usage and performance
CREATE TABLE IF NOT EXISTS ui_component_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component_name VARCHAR(100) NOT NULL, -- dashboard, compliance, performance, etc.
    page_path VARCHAR(255) NOT NULL,
    load_time_ms INTEGER NOT NULL,
    interaction_type VARCHAR(50), -- click, hover, scroll, etc.
    user_session_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB, -- Additional component-specific data
    
    CONSTRAINT valid_load_time CHECK (load_time_ms >= 0),
    CONSTRAINT valid_interaction_type CHECK (interaction_type IN ('click', 'hover', 'scroll', 'focus', 'submit', 'load'))
);

-- Table for storing user interface preferences and settings
CREATE TABLE IF NOT EXISTS ui_user_preferences (
    preference_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_identifier VARCHAR(255) NOT NULL, -- IP or session-based identifier
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_user_preference UNIQUE (user_identifier, preference_key)
);

-- Table for tracking dashboard widget configurations
CREATE TABLE IF NOT EXISTS ui_dashboard_widgets (
    widget_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    widget_type VARCHAR(50) NOT NULL, -- metric_card, agent_status, activity_feed, etc.
    widget_config JSONB NOT NULL,
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    width INTEGER DEFAULT 1,
    height INTEGER DEFAULT 1,
    is_visible BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_widget_type CHECK (widget_type IN ('metric_card', 'agent_status', 'activity_feed', 'upload_zone', 'chart', 'table')),
    CONSTRAINT valid_position CHECK (position_x >= 0 AND position_y >= 0),
    CONSTRAINT valid_dimensions CHECK (width > 0 AND height > 0)
);

-- Table for storing UI error logs and debugging information
CREATE TABLE IF NOT EXISTS ui_error_logs (
    error_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    error_type VARCHAR(50) NOT NULL, -- javascript, api, rendering, etc.
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    page_url VARCHAR(500),
    user_agent TEXT,
    user_session_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_resolved BOOLEAN DEFAULT false,
    resolution_notes TEXT,
    
    CONSTRAINT valid_error_type CHECK (error_type IN ('javascript', 'api', 'rendering', 'network', 'validation'))
);

-- Indexes for UI tables
CREATE INDEX IF NOT EXISTS idx_ui_themes_active ON ui_themes (is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_ui_themes_name ON ui_themes (theme_name);

CREATE INDEX IF NOT EXISTS idx_ui_component_metrics_component ON ui_component_metrics (component_name);
CREATE INDEX IF NOT EXISTS idx_ui_component_metrics_timestamp ON ui_component_metrics (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ui_component_metrics_session ON ui_component_metrics (user_session_id);
CREATE INDEX IF NOT EXISTS idx_ui_component_metrics_page ON ui_component_metrics (page_path);

CREATE INDEX IF NOT EXISTS idx_ui_user_preferences_user ON ui_user_preferences (user_identifier);
CREATE INDEX IF NOT EXISTS idx_ui_user_preferences_key ON ui_user_preferences (preference_key);

CREATE INDEX IF NOT EXISTS idx_ui_dashboard_widgets_type ON ui_dashboard_widgets (widget_type);
CREATE INDEX IF NOT EXISTS idx_ui_dashboard_widgets_visible ON ui_dashboard_widgets (is_visible) WHERE is_visible = true;
CREATE INDEX IF NOT EXISTS idx_ui_dashboard_widgets_position ON ui_dashboard_widgets (position_x, position_y);

CREATE INDEX IF NOT EXISTS idx_ui_error_logs_type ON ui_error_logs (error_type);
CREATE INDEX IF NOT EXISTS idx_ui_error_logs_timestamp ON ui_error_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ui_error_logs_unresolved ON ui_error_logs (is_resolved) WHERE is_resolved = false;

-- Triggers for UI tables
CREATE OR REPLACE FUNCTION update_ui_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_ui_themes_updated_at
    BEFORE UPDATE ON ui_themes
    FOR EACH ROW
    EXECUTE FUNCTION update_ui_updated_at();

CREATE TRIGGER update_ui_user_preferences_updated_at
    BEFORE UPDATE ON ui_user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_ui_updated_at();

CREATE TRIGGER update_ui_dashboard_widgets_updated_at
    BEFORE UPDATE ON ui_dashboard_widgets
    FOR EACH ROW
    EXECUTE FUNCTION update_ui_updated_at();

-- Insert default UI theme
INSERT INTO ui_themes (theme_name, theme_config, is_active, created_by) VALUES 
('ComplianceAI Professional', '{
    "brand_colors": {
        "primary_50": "#f0f4ff",
        "primary_100": "#e0e7ff",
        "primary_200": "#c7d2fe",
        "primary_300": "#a5b4fc",
        "primary_400": "#818cf8",
        "primary_500": "#6366f1",
        "primary_600": "#4f46e5",
        "primary_700": "#4338ca",
        "primary_800": "#3730a3",
        "primary_900": "#312e81"
    },
    "typography": {
        "font_family": "Inter",
        "font_mono": "JetBrains Mono"
    },
    "layout": {
        "container_max_width": "1280px",
        "header_height": "4rem",
        "nav_height": "3.5rem"
    },
    "components": {
        "card_border_radius": "1rem",
        "button_border_radius": "0.5rem",
        "input_border_radius": "0.5rem"
    }
}', true, 'system')
ON CONFLICT (theme_name) DO UPDATE SET 
    theme_config = EXCLUDED.theme_config,
    updated_at = CURRENT_TIMESTAMP;

-- Insert default dashboard widgets
INSERT INTO ui_dashboard_widgets (widget_type, widget_config, position_x, position_y, width, height) VALUES 
('metric_card', '{"title": "Cases Processed", "metric_key": "total_cases", "icon": "document"}', 0, 0, 1, 1),
('metric_card', '{"title": "Processing Time", "metric_key": "processing_time", "icon": "clock"}', 1, 0, 1, 1),
('metric_card', '{"title": "Success Rate", "metric_key": "success_rate", "icon": "check"}', 2, 0, 1, 1),
('metric_card', '{"title": "Cost per Case", "metric_key": "cost_per_case", "icon": "currency"}', 3, 0, 1, 1),
('agent_status', '{"title": "Agent Status", "show_avatars": true}', 0, 1, 2, 1),
('upload_zone', '{"title": "Document Upload", "accepted_types": [".pdf", ".jpg", ".png"]}', 2, 1, 1, 1),
('activity_feed', '{"title": "Recent Activity", "max_items": 10}', 3, 1, 1, 1)
ON CONFLICT DO NOTHING;

-- Comments for UI tables
COMMENT ON TABLE ui_themes IS 'Stores UI theme configurations and customizations';
COMMENT ON TABLE ui_component_metrics IS 'Tracks UI component usage and performance metrics';
COMMENT ON TABLE ui_user_preferences IS 'Stores user interface preferences and settings';
COMMENT ON TABLE ui_dashboard_widgets IS 'Manages dashboard widget configurations and layouts';
COMMENT ON TABLE ui_error_logs IS 'Logs UI errors and debugging information';

-- Schema version: 4.0.0 (Enhanced 3-Agent Architecture with Regulatory Reporting System)
-- Last updated: 2024-09-01
-- =============================================================================
-- RESILIENCE MANAGER TABLES (Phase 2.6)
-- =============================================================================

-- Resilience Manager Tables (Phase 2.6)
CREATE TABLE IF NOT EXISTS regulatory_failure_log (
    failure_id UUID PRIMARY KEY,
    component VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    failure_type VARCHAR(50) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    context JSONB,
    retry_count INTEGER DEFAULT 0,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_method VARCHAR(100)
);

-- Indexes for regulatory_failure_log
CREATE INDEX IF NOT EXISTS idx_regulatory_failure_log_component ON regulatory_failure_log (component);
CREATE INDEX IF NOT EXISTS idx_regulatory_failure_log_timestamp ON regulatory_failure_log (timestamp);
CREATE INDEX IF NOT EXISTS idx_regulatory_failure_log_failure_type ON regulatory_failure_log (failure_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_failure_log_resolved ON regulatory_failure_log (resolved);
CREATE INDEX IF NOT EXISTS idx_regulatory_failure_log_component_timestamp ON regulatory_failure_log (component, timestamp);

-- Circuit breaker state tracking
CREATE TABLE IF NOT EXISTS regulatory_circuit_breaker_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component VARCHAR(100) NOT NULL,
    from_state VARCHAR(20),
    to_state VARCHAR(20) NOT NULL,
    failure_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    trigger_reason TEXT,
    recovery_time_seconds INTEGER
);

-- Indexes for regulatory_circuit_breaker_log
CREATE INDEX IF NOT EXISTS idx_regulatory_circuit_breaker_component ON regulatory_circuit_breaker_log (component);
CREATE INDEX IF NOT EXISTS idx_regulatory_circuit_breaker_timestamp ON regulatory_circuit_breaker_log (timestamp);
CREATE INDEX IF NOT EXISTS idx_regulatory_circuit_breaker_state ON regulatory_circuit_breaker_log (to_state);

-- DLQ message tracking
CREATE TABLE IF NOT EXISTS regulatory_dlq_messages (
    message_id UUID PRIMARY KEY,
    original_topic VARCHAR(100) NOT NULL,
    original_key TEXT,
    original_value BYTEA,
    error_type VARCHAR(50) NOT NULL,
    error_message TEXT NOT NULL,
    failure_count INTEGER DEFAULT 1,
    first_failure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    last_failure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    headers JSONB,
    context JSONB,
    recovery_attempted BOOLEAN DEFAULT FALSE,
    recovery_successful BOOLEAN DEFAULT FALSE,
    recovery_timestamp TIMESTAMP WITH TIME ZONE
);

-- Indexes for regulatory_dlq_messages
CREATE INDEX IF NOT EXISTS idx_regulatory_dlq_original_topic ON regulatory_dlq_messages (original_topic);
CREATE INDEX IF NOT EXISTS idx_regulatory_dlq_error_type ON regulatory_dlq_messages (error_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_dlq_first_failure ON regulatory_dlq_messages (first_failure_time);
CREATE INDEX IF NOT EXISTS idx_regulatory_dlq_recovery ON regulatory_dlq_messages (recovery_attempted, recovery_successful);

-- Resilience metrics aggregation table
CREATE TABLE IF NOT EXISTS regulatory_resilience_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- 'retry_attempts', 'circuit_breaker_trips', 'dlq_messages', etc.
    metric_value INTEGER NOT NULL,
    aggregation_period VARCHAR(20) NOT NULL, -- 'hourly', 'daily', 'weekly'
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for regulatory_resilience_metrics
CREATE INDEX IF NOT EXISTS idx_regulatory_resilience_metrics_component ON regulatory_resilience_metrics (component);
CREATE INDEX IF NOT EXISTS idx_regulatory_resilience_metrics_type ON regulatory_resilience_metrics (metric_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_resilience_metrics_period ON regulatory_resilience_metrics (period_start, period_end);
CREATE UNIQUE INDEX IF NOT EXISTS idx_regulatory_resilience_metrics_unique ON regulatory_resilience_metrics (component, metric_type, aggregation_period, period_start);

-- Triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_regulatory_failure_log_resolved_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.resolved_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS trigger_regulatory_failure_log_resolved
    BEFORE UPDATE ON regulatory_failure_log
    FOR EACH ROW
    WHEN (OLD.resolved = FALSE AND NEW.resolved = TRUE)
    EXECUTE FUNCTION update_regulatory_failure_log_resolved_at();

-- End of schema
-- =============================================================================
-- REGULATORY REPORTING SYSTEM TABLES (Added for RegReporting v4.0.0)
-- =============================================================================

-- Table for storing regulatory obligations from various sources
CREATE TABLE IF NOT EXISTS regulatory_obligations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regulation_name VARCHAR(255) NOT NULL,
    article VARCHAR(100),
    clause VARCHAR(100),
    jurisdiction CHAR(2) NOT NULL, -- ISO 3166-1 alpha-2 country codes
    effective_date DATE,
    content TEXT NOT NULL,
    version VARCHAR(50) NOT NULL,
    source_publisher VARCHAR(255) NOT NULL,
    source_url TEXT,
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    
    -- Regulatory categorization
    regulation_type VARCHAR(50) NOT NULL, -- Basel III, PSD2, DORA, AI Act, etc.
    level VARCHAR(10) CHECK (level IN ('Level 1', 'Level 2', 'Level 3')),
    priority INTEGER CHECK (priority >= 1 AND priority <= 10) DEFAULT 5,
    
    -- Content metadata
    content_hash VARCHAR(64), -- SHA-256 hash for change detection
    language CHAR(2) DEFAULT 'en',
    document_type VARCHAR(50), -- PDF, HTML, XML, etc.
    
    CONSTRAINT unique_obligation_version UNIQUE (regulation_name, article, clause, jurisdiction, version)
);

-- Table for tracking regulatory obligation changes and versions
CREATE TABLE IF NOT EXISTS regulatory_obligation_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    obligation_id UUID NOT NULL REFERENCES regulatory_obligations(id),
    change_type VARCHAR(20) NOT NULL CHECK (change_type IN ('created', 'updated', 'deleted', 'superseded')),
    old_version VARCHAR(50),
    new_version VARCHAR(50),
    changes JSONB, -- Detailed change information
    changed_by VARCHAR(255) DEFAULT 'system',
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Table for compiled regulatory rules (JSON-Logic format)
CREATE TABLE IF NOT EXISTS regulatory_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    obligation_id UUID NOT NULL REFERENCES regulatory_obligations(id),
    rule_name VARCHAR(255) NOT NULL,
    rule_logic JSONB NOT NULL, -- JSON-Logic rule definition
    jurisdiction CHAR(2) NOT NULL,
    regulation_type VARCHAR(50) NOT NULL,
    
    -- Rule metadata
    compiled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    compiled_by VARCHAR(255) DEFAULT 'rule_compiler',
    is_active BOOLEAN DEFAULT true,
    priority INTEGER CHECK (priority >= 1 AND priority <= 10) DEFAULT 5,
    
    -- Performance and validation
    compilation_confidence DECIMAL(3,2) CHECK (compilation_confidence >= 0.0 AND compilation_confidence <= 1.0),
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'validated', 'failed', 'deprecated')),
    last_validated TIMESTAMP WITH TIME ZONE,
    
    -- Rule relationships
    parent_rule_id UUID REFERENCES regulatory_rules(rule_id),
    supersedes_rule_id UUID REFERENCES regulatory_rules(rule_id),
    
    CONSTRAINT unique_active_rule UNIQUE (rule_name, jurisdiction, regulation_type) DEFERRABLE INITIALLY DEFERRED
);

-- Table for managing jurisdiction-specific configurations
CREATE TABLE IF NOT EXISTS regulatory_jurisdictions (
    jurisdiction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    country_code CHAR(2) NOT NULL UNIQUE,
    country_name VARCHAR(100) NOT NULL,
    regulatory_authority VARCHAR(255),
    authority_website TEXT,
    
    -- Configuration
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5,
    local_overrides JSONB, -- Country-specific rule modifications
    
    -- Contact and integration info
    contact_email VARCHAR(255),
    api_endpoint TEXT,
    feed_urls JSONB, -- RSS/API feeds for this jurisdiction
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for tracking regulatory feed sources and their health
CREATE TABLE IF NOT EXISTS regulatory_feed_sources (
    source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('RSS', 'API', 'SCRAPER', 'MANUAL')),
    source_url TEXT NOT NULL,
    jurisdiction CHAR(2) REFERENCES regulatory_jurisdictions(country_code),
    
    -- Feed configuration
    polling_interval INTEGER DEFAULT 3600, -- seconds
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5,
    
    -- Authentication and headers
    auth_config JSONB, -- API keys, credentials, etc.
    request_headers JSONB,
    
    -- Health monitoring
    last_successful_poll TIMESTAMP WITH TIME ZONE,
    last_failed_poll TIMESTAMP WITH TIME ZONE,
    consecutive_failures INTEGER DEFAULT 0,
    health_status VARCHAR(20) DEFAULT 'unknown' CHECK (health_status IN ('healthy', 'degraded', 'failed', 'unknown')),
    
    -- Statistics
    total_polls INTEGER DEFAULT 0,
    successful_polls INTEGER DEFAULT 0,
    total_obligations_found INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for compliance report generation and tracking
CREATE TABLE IF NOT EXISTS regulatory_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_type VARCHAR(50) NOT NULL, -- FINREP, COREP, DORA, etc.
    report_format VARCHAR(20) NOT NULL CHECK (report_format IN ('XBRL', 'CSV', 'JSON', 'XML')),
    jurisdiction CHAR(2) NOT NULL,
    
    -- Report metadata
    reporting_period_start DATE NOT NULL,
    reporting_period_end DATE NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    generated_by VARCHAR(255) DEFAULT 'system',
    
    -- Content and delivery
    report_content JSONB, -- Report data structure
    file_path TEXT, -- Generated file location
    file_size BIGINT,
    checksum VARCHAR(64),
    
    -- Delivery tracking
    delivery_status VARCHAR(20) DEFAULT 'pending' CHECK (delivery_status IN ('pending', 'delivered', 'failed', 'retrying')),
    delivery_method VARCHAR(20) CHECK (delivery_method IN ('SFTP', 'API', 'EMAIL', 'MANUAL')),
    delivered_at TIMESTAMP WITH TIME ZONE,
    delivery_attempts INTEGER DEFAULT 0,
    delivery_error TEXT,
    
    -- Regulatory requirements
    deadline DATE,
    is_mandatory BOOLEAN DEFAULT true,
    regulatory_reference TEXT,
    
    -- Validation
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'passed', 'failed')),
    validation_errors JSONB,
    validated_at TIMESTAMP WITH TIME ZONE
);

-- Table for audit trail of all regulatory system activities
CREATE TABLE IF NOT EXISTS regulatory_audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL, -- obligation_created, rule_compiled, report_generated, etc.
    entity_type VARCHAR(50) NOT NULL, -- obligation, rule, report, etc.
    entity_id UUID NOT NULL,
    
    -- Event details
    event_data JSONB NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_by VARCHAR(255) NOT NULL,
    
    -- Context
    session_id UUID,
    correlation_id UUID,
    jurisdiction CHAR(2),
    regulation_type VARCHAR(50),
    
    -- Impact assessment
    impact_level VARCHAR(10) CHECK (impact_level IN ('low', 'medium', 'high', 'critical')) DEFAULT 'medium',
    affected_systems JSONB,
    
    -- Additional metadata
    user_agent TEXT,
    ip_address INET,
    additional_context JSONB
);

-- Table for managing regulatory deadlines and scheduling
CREATE TABLE IF NOT EXISTS regulatory_deadlines (
    deadline_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regulation_name VARCHAR(255) NOT NULL,
    jurisdiction CHAR(2) NOT NULL,
    deadline_type VARCHAR(50) NOT NULL, -- implementation, reporting, compliance, etc.
    
    -- Deadline information
    deadline_date DATE NOT NULL,
    description TEXT NOT NULL,
    regulatory_reference TEXT,
    
    -- Notification and scheduling
    advance_notice_days INTEGER DEFAULT 30,
    notification_sent BOOLEAN DEFAULT false,
    notification_sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'notified', 'completed', 'missed', 'cancelled')),
    completed_at TIMESTAMP WITH TIME ZONE,
    completion_notes TEXT,
    
    -- Automation
    auto_trigger_reports BOOLEAN DEFAULT false,
    report_types JSONB, -- Array of report types to generate
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for regulatory tables
CREATE INDEX IF NOT EXISTS idx_regulatory_obligations_jurisdiction ON regulatory_obligations (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_regulatory_obligations_regulation_type ON regulatory_obligations (regulation_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_obligations_effective_date ON regulatory_obligations (effective_date);
CREATE INDEX IF NOT EXISTS idx_regulatory_obligations_active ON regulatory_obligations (is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_regulatory_obligations_content_hash ON regulatory_obligations (content_hash);
CREATE INDEX IF NOT EXISTS idx_regulatory_obligations_retrieved_at ON regulatory_obligations (retrieved_at DESC);

CREATE INDEX IF NOT EXISTS idx_regulatory_obligation_history_obligation_id ON regulatory_obligation_history (obligation_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_obligation_history_changed_at ON regulatory_obligation_history (changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_regulatory_obligation_history_change_type ON regulatory_obligation_history (change_type);

CREATE INDEX IF NOT EXISTS idx_regulatory_rules_obligation_id ON regulatory_rules (obligation_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_rules_jurisdiction ON regulatory_rules (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_regulatory_rules_regulation_type ON regulatory_rules (regulation_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_rules_active ON regulatory_rules (is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_regulatory_rules_priority ON regulatory_rules (priority DESC);
CREATE INDEX IF NOT EXISTS idx_regulatory_rules_compiled_at ON regulatory_rules (compiled_at DESC);

CREATE INDEX IF NOT EXISTS idx_regulatory_jurisdictions_country_code ON regulatory_jurisdictions (country_code);
CREATE INDEX IF NOT EXISTS idx_regulatory_jurisdictions_active ON regulatory_jurisdictions (is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_regulatory_feed_sources_jurisdiction ON regulatory_feed_sources (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_regulatory_feed_sources_active ON regulatory_feed_sources (is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_regulatory_feed_sources_health ON regulatory_feed_sources (health_status);
CREATE INDEX IF NOT EXISTS idx_regulatory_feed_sources_last_poll ON regulatory_feed_sources (last_successful_poll DESC);

CREATE INDEX IF NOT EXISTS idx_regulatory_reports_type ON regulatory_reports (report_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_reports_jurisdiction ON regulatory_reports (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_regulatory_reports_period ON regulatory_reports (reporting_period_start, reporting_period_end);
CREATE INDEX IF NOT EXISTS idx_regulatory_reports_generated_at ON regulatory_reports (generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_regulatory_reports_delivery_status ON regulatory_reports (delivery_status);
CREATE INDEX IF NOT EXISTS idx_regulatory_reports_deadline ON regulatory_reports (deadline);

CREATE INDEX IF NOT EXISTS idx_regulatory_audit_logs_event_type ON regulatory_audit_logs (event_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_audit_logs_entity ON regulatory_audit_logs (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_audit_logs_occurred_at ON regulatory_audit_logs (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_regulatory_audit_logs_jurisdiction ON regulatory_audit_logs (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_regulatory_audit_logs_correlation ON regulatory_audit_logs (correlation_id);

CREATE INDEX IF NOT EXISTS idx_regulatory_deadlines_jurisdiction ON regulatory_deadlines (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_regulatory_deadlines_date ON regulatory_deadlines (deadline_date);
CREATE INDEX IF NOT EXISTS idx_regulatory_deadlines_status ON regulatory_deadlines (status);
CREATE INDEX IF NOT EXISTS idx_regulatory_deadlines_auto_trigger ON regulatory_deadlines (auto_trigger_reports) WHERE auto_trigger_reports = true;

-- Triggers for regulatory tables
CREATE OR REPLACE FUNCTION update_regulatory_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_regulatory_obligations_updated_at
    BEFORE UPDATE ON regulatory_obligations
    FOR EACH ROW
    EXECUTE FUNCTION update_regulatory_updated_at();

CREATE TRIGGER trigger_regulatory_jurisdictions_updated_at
    BEFORE UPDATE ON regulatory_jurisdictions
    FOR EACH ROW
    EXECUTE FUNCTION update_regulatory_updated_at();

CREATE TRIGGER trigger_regulatory_feed_sources_updated_at
    BEFORE UPDATE ON regulatory_feed_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_regulatory_updated_at();

CREATE TRIGGER trigger_regulatory_deadlines_updated_at
    BEFORE UPDATE ON regulatory_deadlines
    FOR EACH ROW
    EXECUTE FUNCTION update_regulatory_updated_at();

-- Insert default jurisdictions and feed sources
INSERT INTO regulatory_jurisdictions (country_code, country_name, regulatory_authority, authority_website, feed_urls) VALUES 
('DE', 'Germany', 'BaFin (Federal Financial Supervisory Authority)', 'https://www.bafin.de', '{"rss": ["https://www.bafin.de/SharedDocs/Veroeffentlichungen/DE/rss.xml"], "api": []}'),
('IE', 'Ireland', 'Central Bank of Ireland', 'https://www.centralbank.ie', '{"rss": ["https://www.centralbank.ie/news/rss"], "api": []}'),
('EU', 'European Union', 'European Banking Authority (EBA)', 'https://www.eba.europa.eu', '{"rss": ["https://www.eba.europa.eu/rss.xml"], "api": ["https://www.eba.europa.eu/api/v1/"]}'),
('GB', 'United Kingdom', 'Financial Conduct Authority (FCA)', 'https://www.fca.org.uk', '{"rss": ["https://www.fca.org.uk/news/rss.xml"], "api": []}')
ON CONFLICT (country_code) DO UPDATE SET 
    country_name = EXCLUDED.country_name,
    regulatory_authority = EXCLUDED.regulatory_authority,
    authority_website = EXCLUDED.authority_website,
    feed_urls = EXCLUDED.feed_urls,
    updated_at = CURRENT_TIMESTAMP;

-- Insert default feed sources
INSERT INTO regulatory_feed_sources (source_name, source_type, source_url, jurisdiction, polling_interval) VALUES 
('EUR-Lex RSS Feed', 'RSS', 'https://eur-lex.europa.eu/EN/rss/rss_derniers_documents_publies.xml', 'EU', 3600),
('EBA Publications RSS', 'RSS', 'https://www.eba.europa.eu/rss.xml', 'EU', 7200),
('BaFin News RSS', 'RSS', 'https://www.bafin.de/SharedDocs/Veroeffentlichungen/DE/rss.xml', 'DE', 7200),
('Central Bank of Ireland RSS', 'RSS', 'https://www.centralbank.ie/news/rss', 'IE', 7200),
('FCA News RSS', 'RSS', 'https://www.fca.org.uk/news/rss.xml', 'GB', 7200)
ON CONFLICT DO NOTHING;

-- Insert sample regulatory deadlines
INSERT INTO regulatory_deadlines (regulation_name, jurisdiction, deadline_type, deadline_date, description, regulatory_reference, advance_notice_days, auto_trigger_reports, report_types) VALUES 
('Basel III Capital Requirements', 'EU', 'reporting', '2024-12-31', 'Annual Basel III capital adequacy reporting deadline', 'CRR Article 430', 60, true, '["COREP", "FINREP"]'),
('PSD2 Operational Resilience', 'EU', 'compliance', '2024-06-30', 'PSD2 operational resilience requirements implementation', 'PSD2 Article 95', 90, false, '[]'),
('DORA ICT Risk Management', 'EU', 'reporting', '2024-09-30', 'DORA ICT risk management framework reporting', 'DORA Article 16', 45, true, '["DORA"]'),
('AI Act Compliance Assessment', 'EU', 'compliance', '2025-02-02', 'AI Act high-risk system compliance assessment', 'AI Act Article 43', 120, false, '[]')
ON CONFLICT DO NOTHING;

-- Comments for regulatory tables
COMMENT ON TABLE regulatory_obligations IS 'Stores regulatory obligations parsed from various sources (EUR-Lex, EBA, national authorities)';
COMMENT ON TABLE regulatory_obligation_history IS 'Tracks all changes to regulatory obligations for audit and rollback purposes';
COMMENT ON TABLE regulatory_rules IS 'Compiled JSON-Logic rules generated from regulatory obligations';
COMMENT ON TABLE regulatory_jurisdictions IS 'Configuration and metadata for different regulatory jurisdictions';
COMMENT ON TABLE regulatory_feed_sources IS 'RSS/API feed sources for regulatory updates with health monitoring';
COMMENT ON TABLE regulatory_reports IS 'Generated compliance reports (FINREP, COREP, DORA) with delivery tracking';
COMMENT ON TABLE regulatory_audit_logs IS 'Comprehensive audit trail for all regulatory system activities';
COMMENT ON TABLE regulatory_deadlines IS 'Regulatory deadlines and automated scheduling for compliance activities';

-- =====================================================
-- REGULATORY DOCUMENT PROCESSING QUEUE (Phase 2.2)
-- =====================================================

-- Table for storing discovered documents awaiting processing
CREATE TABLE IF NOT EXISTS regulatory_documents_queue (
    document_id VARCHAR(32) PRIMARY KEY,
    source_id VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_date TIMESTAMP WITH TIME ZONE,
    updated_date TIMESTAMP WITH TIME ZONE,
    content_type VARCHAR(100),
    content_hash VARCHAR(64),
    regulation_type VARCHAR(50),
    article_number VARCHAR(20),
    language VARCHAR(5) DEFAULT 'en',
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(20) DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'skipped')),
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    processing_error TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient document queue processing
CREATE INDEX IF NOT EXISTS idx_regulatory_documents_queue_status ON regulatory_documents_queue(processing_status);
CREATE INDEX IF NOT EXISTS idx_regulatory_documents_queue_priority ON regulatory_documents_queue(priority DESC, discovered_at ASC);
CREATE INDEX IF NOT EXISTS idx_regulatory_documents_queue_source ON regulatory_documents_queue(source_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_documents_queue_discovered ON regulatory_documents_queue(discovered_at);
CREATE INDEX IF NOT EXISTS idx_regulatory_documents_queue_regulation_type ON regulatory_documents_queue(regulation_type);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_regulatory_documents_queue_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_regulatory_documents_queue_updated_at
    BEFORE UPDATE ON regulatory_documents_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_regulatory_documents_queue_updated_at();

-- Comments for document queue table
COMMENT ON TABLE regulatory_documents_queue IS 'Queue for regulatory documents discovered by feed scheduler awaiting processing';
COMMENT ON COLUMN regulatory_documents_queue.document_id IS 'Unique identifier for the document (SHA-256 hash)';
COMMENT ON COLUMN regulatory_documents_queue.source_id IS 'Reference to regulatory_feed_sources.source_id';
COMMENT ON COLUMN regulatory_documents_queue.priority IS 'Processing priority (1=highest, 10=lowest)';
COMMENT ON COLUMN regulatory_documents_queue.processing_status IS 'Current processing status of the document';
COMMENT ON COLUMN regulatory_documents_queue.retry_count IS 'Number of processing retry attempts';

-- =============================================================================
-- PHASE 3: INTELLIGENCE & COMPLIANCE AGENT ENHANCEMENT TABLES
-- =============================================================================

-- Jurisdiction configurations for rule filtering
CREATE TABLE IF NOT EXISTS jurisdiction_configs (
    jurisdiction_code VARCHAR(10) PRIMARY KEY,
    jurisdiction_name VARCHAR(255) NOT NULL,
    jurisdiction_level VARCHAR(50) NOT NULL DEFAULT 'national', -- international, supranational, national, regional, local
    parent_jurisdictions TEXT[], -- Array of parent jurisdiction codes
    child_jurisdictions TEXT[], -- Array of child jurisdiction codes
    supported_regulations TEXT[], -- Array of supported regulation types
    regulatory_authorities TEXT[], -- Array of regulatory body names
    language_codes TEXT[], -- Array of supported language codes
    currency_codes TEXT[], -- Array of supported currency codes
    timezone VARCHAR(100) DEFAULT 'UTC',
    business_days INTEGER[] DEFAULT '{0,1,2,3,4}', -- 0=Monday, 6=Sunday
    status VARCHAR(50) DEFAULT 'active', -- active, inactive, pending, deprecated
    effective_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for jurisdiction_configs
CREATE INDEX IF NOT EXISTS idx_jurisdiction_configs_status ON jurisdiction_configs (status);
CREATE INDEX IF NOT EXISTS idx_jurisdiction_configs_level ON jurisdiction_configs (jurisdiction_level);
CREATE INDEX IF NOT EXISTS idx_jurisdiction_configs_effective_date ON jurisdiction_configs (effective_date);

-- Customer jurisdiction information
CREATE TABLE IF NOT EXISTS customer_jurisdictions (
    customer_id VARCHAR(100) PRIMARY KEY,
    primary_jurisdiction VARCHAR(10) NOT NULL,
    secondary_jurisdictions TEXT[], -- Array of additional jurisdictions
    residence_country VARCHAR(10),
    citizenship_countries TEXT[], -- Array of citizenship countries
    business_countries TEXT[], -- Array of business operation countries
    tax_jurisdictions TEXT[], -- Array of tax reporting jurisdictions
    confidence_score DECIMAL(5,4) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    detection_method VARCHAR(100) DEFAULT 'automated_analysis',
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Indexes for customer_jurisdictions
CREATE INDEX IF NOT EXISTS idx_customer_jurisdictions_primary ON customer_jurisdictions (primary_jurisdiction);
CREATE INDEX IF NOT EXISTS idx_customer_jurisdictions_confidence ON customer_jurisdictions (confidence_score);
CREATE INDEX IF NOT EXISTS idx_customer_jurisdictions_detected_at ON customer_jurisdictions (detected_at);

-- Jurisdiction conflicts and resolutions
CREATE TABLE IF NOT EXISTS jurisdiction_conflicts (
    conflict_id VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    conflicting_jurisdictions TEXT[] NOT NULL, -- Array of conflicting jurisdiction codes
    conflicting_rules TEXT[] NOT NULL, -- Array of conflicting rule IDs
    conflict_type VARCHAR(100) NOT NULL,
    resolution_strategy VARCHAR(100) NOT NULL, -- most_restrictive, highest_precedence, customer_preference, manual_review
    resolved_jurisdiction VARCHAR(10),
    resolution_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Foreign key
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Indexes for jurisdiction_conflicts
CREATE INDEX IF NOT EXISTS idx_jurisdiction_conflicts_customer_id ON jurisdiction_conflicts (customer_id);
CREATE INDEX IF NOT EXISTS idx_jurisdiction_conflicts_created_at ON jurisdiction_conflicts (created_at);
CREATE INDEX IF NOT EXISTS idx_jurisdiction_conflicts_resolved_at ON jurisdiction_conflicts (resolved_at);
CREATE INDEX IF NOT EXISTS idx_jurisdiction_conflicts_strategy ON jurisdiction_conflicts (resolution_strategy);

-- Rule overlaps and clustering
CREATE TABLE IF NOT EXISTS rule_overlaps (
    cluster_id VARCHAR(100) PRIMARY KEY,
    obligation_ids TEXT[] NOT NULL, -- Array of overlapping obligation IDs
    cluster_type VARCHAR(50) NOT NULL, -- identical, semantic, partial, hierarchical, conflicting, complementary
    primary_obligation_id VARCHAR(100) NOT NULL,
    similarity_matrix JSONB, -- Pairwise similarity scores
    regulatory_levels JSONB, -- Regulatory level of each obligation
    resolution_strategy VARCHAR(100) NOT NULL, -- merge, prioritize, preserve_all, escalate
    merged_obligation_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for rule_overlaps
CREATE INDEX IF NOT EXISTS idx_rule_overlaps_cluster_type ON rule_overlaps (cluster_type);
CREATE INDEX IF NOT EXISTS idx_rule_overlaps_primary_obligation ON rule_overlaps (primary_obligation_id);
CREATE INDEX IF NOT EXISTS idx_rule_overlaps_created_at ON rule_overlaps (created_at);
CREATE INDEX IF NOT EXISTS idx_rule_overlaps_resolved_at ON rule_overlaps (resolved_at);
CREATE INDEX IF NOT EXISTS idx_rule_overlaps_strategy ON rule_overlaps (resolution_strategy);

-- Merged obligations from overlap resolution
CREATE TABLE IF NOT EXISTS merged_obligations (
    merged_id VARCHAR(100) PRIMARY KEY,
    source_obligation_ids TEXT[] NOT NULL, -- Array of source obligation IDs
    merged_content TEXT NOT NULL,
    merged_requirements TEXT[], -- Array of consolidated requirements
    precedence_rules JSONB, -- Rules for handling conflicts
    traceability_map JSONB, -- Map requirements to source obligations
    confidence_score DECIMAL(5,4) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for merged_obligations
CREATE INDEX IF NOT EXISTS idx_merged_obligations_confidence ON merged_obligations (confidence_score);
CREATE INDEX IF NOT EXISTS idx_merged_obligations_created_at ON merged_obligations (created_at);

-- Enhanced audit logs for Phase 3 activities
CREATE TABLE IF NOT EXISTS audit_exports (
    export_id VARCHAR(100) PRIMARY KEY,
    query_params JSONB NOT NULL,
    format VARCHAR(20) NOT NULL, -- json, csv, xml, pdf
    include_metadata BOOLEAN DEFAULT true,
    include_sensitive_data BOOLEAN DEFAULT false,
    encryption_required BOOLEAN DEFAULT false,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    file_path TEXT,
    file_size BIGINT,
    download_count INTEGER DEFAULT 0
);

-- Indexes for audit_exports
CREATE INDEX IF NOT EXISTS idx_audit_exports_created_by ON audit_exports (created_by);
CREATE INDEX IF NOT EXISTS idx_audit_exports_created_at ON audit_exports (created_at);
CREATE INDEX IF NOT EXISTS idx_audit_exports_expires_at ON audit_exports (expires_at);
CREATE INDEX IF NOT EXISTS idx_audit_exports_format ON audit_exports (format);

-- Rule compilation results and metadata
CREATE TABLE IF NOT EXISTS rule_compilation_results (
    compilation_id VARCHAR(100) PRIMARY KEY,
    obligation_id VARCHAR(100) NOT NULL,
    compiled_rules_count INTEGER DEFAULT 0,
    compilation_time_ms DECIMAL(10,3),
    confidence_score DECIMAL(5,4) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    compilation_metadata JSONB,
    errors JSONB, -- Array of compilation errors if any
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key
    FOREIGN KEY (obligation_id) REFERENCES regulatory_obligations(obligation_id) ON DELETE CASCADE
);

-- Indexes for rule_compilation_results
CREATE INDEX IF NOT EXISTS idx_rule_compilation_obligation_id ON rule_compilation_results (obligation_id);
CREATE INDEX IF NOT EXISTS idx_rule_compilation_created_at ON rule_compilation_results (created_at);
CREATE INDEX IF NOT EXISTS idx_rule_compilation_confidence ON rule_compilation_results (confidence_score);
CREATE INDEX IF NOT EXISTS idx_rule_compilation_time ON rule_compilation_results (compilation_time_ms);

-- Kafka consumer state and performance tracking
CREATE TABLE IF NOT EXISTS kafka_consumer_state (
    consumer_group VARCHAR(255) PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,
    partition_offsets JSONB, -- Current offsets per partition
    lag_metrics JSONB, -- Consumer lag information
    processing_stats JSONB, -- Processing statistics
    last_message_timestamp TIMESTAMP WITH TIME ZONE,
    last_commit_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active', -- active, paused, error, stopped
    error_details TEXT
);

-- Kafka Dead Letter Queue messages
CREATE TABLE IF NOT EXISTS kafka_dlq_messages (
    message_id VARCHAR(100) PRIMARY KEY,
    original_topic VARCHAR(255) NOT NULL,
    dlq_topic VARCHAR(255) NOT NULL,
    error_reason TEXT NOT NULL,
    message_data JSONB NOT NULL,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    failed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending' -- pending, retrying, processed, failed
);

-- Indexes for kafka_consumer_state
CREATE INDEX IF NOT EXISTS idx_kafka_consumer_state_topic ON kafka_consumer_state (topic);
CREATE INDEX IF NOT EXISTS idx_kafka_consumer_state_status ON kafka_consumer_state (status);
CREATE INDEX IF NOT EXISTS idx_kafka_consumer_state_last_commit ON kafka_consumer_state (last_commit_timestamp);

-- Indexes for kafka_dlq_messages
CREATE INDEX IF NOT EXISTS idx_kafka_dlq_messages_original_topic ON kafka_dlq_messages (original_topic);
CREATE INDEX IF NOT EXISTS idx_kafka_dlq_messages_dlq_topic ON kafka_dlq_messages (dlq_topic);
CREATE INDEX IF NOT EXISTS idx_kafka_dlq_messages_status ON kafka_dlq_messages (status);
CREATE INDEX IF NOT EXISTS idx_kafka_dlq_messages_failed_at ON kafka_dlq_messages (failed_at);

-- Performance metrics for Phase 3 components
CREATE TABLE IF NOT EXISTS phase3_performance_metrics (
    metric_id VARCHAR(100) PRIMARY KEY,
    component VARCHAR(100) NOT NULL, -- rule_compiler, jurisdiction_handler, overlap_resolver, audit_logger
    operation VARCHAR(100) NOT NULL,
    execution_time_ms DECIMAL(10,3) NOT NULL,
    success BOOLEAN NOT NULL,
    resource_id VARCHAR(100),
    metadata JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for phase3_performance_metrics
CREATE INDEX IF NOT EXISTS idx_phase3_metrics_component ON phase3_performance_metrics (component);
CREATE INDEX IF NOT EXISTS idx_phase3_metrics_operation ON phase3_performance_metrics (operation);
CREATE INDEX IF NOT EXISTS idx_phase3_metrics_recorded_at ON phase3_performance_metrics (recorded_at);
CREATE INDEX IF NOT EXISTS idx_phase3_metrics_success ON phase3_performance_metrics (success);
CREATE INDEX IF NOT EXISTS idx_phase3_metrics_execution_time ON phase3_performance_metrics (execution_time_ms);

-- =============================================================================
-- PHASE 3 TRIGGERS AND FUNCTIONS
-- =============================================================================

-- Update triggers for Phase 3 tables
CREATE TRIGGER trigger_jurisdiction_configs_updated_at
    BEFORE UPDATE ON jurisdiction_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_regulatory_updated_at();

CREATE TRIGGER trigger_customer_jurisdictions_updated_at
    BEFORE UPDATE ON customer_jurisdictions
    FOR EACH ROW
    EXECUTE FUNCTION update_regulatory_updated_at();

-- Function to calculate rule compilation statistics
CREATE OR REPLACE FUNCTION calculate_compilation_stats()
RETURNS TABLE(
    total_compilations BIGINT,
    successful_compilations BIGINT,
    failed_compilations BIGINT,
    avg_compilation_time DECIMAL,
    avg_confidence_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_compilations,
        COUNT(*) FILTER (WHERE errors IS NULL OR jsonb_array_length(errors) = 0) as successful_compilations,
        COUNT(*) FILTER (WHERE errors IS NOT NULL AND jsonb_array_length(errors) > 0) as failed_compilations,
        AVG(compilation_time_ms) as avg_compilation_time,
        AVG(confidence_score) as avg_confidence_score
    FROM rule_compilation_results
    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Function to get jurisdiction hierarchy
CREATE OR REPLACE FUNCTION get_jurisdiction_hierarchy(jurisdiction_code VARCHAR(10))
RETURNS TABLE(
    level INTEGER,
    code VARCHAR(10),
    name VARCHAR(255)
) AS $$
WITH RECURSIVE jurisdiction_tree AS (
    -- Base case: start with the given jurisdiction
    SELECT 1 as level, jc.jurisdiction_code as code, jc.jurisdiction_name as name, jc.parent_jurisdictions
    FROM jurisdiction_configs jc
    WHERE jc.jurisdiction_code = $1
    
    UNION ALL
    
    -- Recursive case: find parent jurisdictions
    SELECT jt.level + 1, jc.jurisdiction_code, jc.jurisdiction_name, jc.parent_jurisdictions
    FROM jurisdiction_tree jt
    CROSS JOIN LATERAL unnest(jt.parent_jurisdictions) AS parent_code
    JOIN jurisdiction_configs jc ON jc.jurisdiction_code = parent_code
    WHERE jt.level < 10 -- Prevent infinite recursion
)
SELECT jt.level, jt.code, jt.name
FROM jurisdiction_tree jt
ORDER BY jt.level;
$$ LANGUAGE sql;

-- =============================================================================
-- PHASE 3 DEFAULT DATA
-- =============================================================================

-- Insert default jurisdiction configurations
INSERT INTO jurisdiction_configs (
    jurisdiction_code, jurisdiction_name, jurisdiction_level, parent_jurisdictions, 
    child_jurisdictions, supported_regulations, regulatory_authorities, 
    language_codes, currency_codes, timezone, business_days
) VALUES 
(
    'EU', 'European Union', 'supranational', '{}', 
    '{"DE","IE","FR","IT","ES","NL","AT","BE","LU","PT","FI","SE","DK","CZ","PL","HU","SK","SI","HR","BG","RO","LV","LT","EE","CY","MT","GR"}',
    '{"AML","KYC","GDPR","PSD2","DORA","MIFID_II","EMIR"}',
    '{"EBA","ECB","ESMA","EIOPA"}',
    '{"en","de","fr","es","it","nl","pt","pl"}',
    '{"EUR"}',
    'Europe/Brussels',
    '{0,1,2,3,4}'
),
(
    'DE', 'Germany', 'national', '{"EU"}', '{}',
    '{"AML","KYC","GDPR","BASEL_III","PSD2","DORA"}',
    '{"BaFin","Bundesbank"}',
    '{"de","en"}',
    '{"EUR"}',
    'Europe/Berlin',
    '{0,1,2,3,4}'
),
(
    'IE', 'Ireland', 'national', '{"EU"}', '{}',
    '{"AML","KYC","GDPR","BASEL_III","PSD2","DORA"}',
    '{"Central Bank of Ireland"}',
    '{"en","ga"}',
    '{"EUR"}',
    'Europe/Dublin',
    '{0,1,2,3,4}'
),
(
    'GB', 'United Kingdom', 'national', '{}', '{}',
    '{"AML","KYC","BASEL_III"}',
    '{"FCA","PRA","Bank of England"}',
    '{"en"}',
    '{"GBP"}',
    'Europe/London',
    '{0,1,2,3,4}'
)
ON CONFLICT (jurisdiction_code) DO UPDATE SET 
    jurisdiction_name = EXCLUDED.jurisdiction_name,
    jurisdiction_level = EXCLUDED.jurisdiction_level,
    parent_jurisdictions = EXCLUDED.parent_jurisdictions,
    child_jurisdictions = EXCLUDED.child_jurisdictions,
    supported_regulations = EXCLUDED.supported_regulations,
    regulatory_authorities = EXCLUDED.regulatory_authorities,
    language_codes = EXCLUDED.language_codes,
    currency_codes = EXCLUDED.currency_codes,
    timezone = EXCLUDED.timezone,
    business_days = EXCLUDED.business_days,
    updated_at = CURRENT_TIMESTAMP;

-- Insert default Kafka consumer state
INSERT INTO kafka_consumer_state (
    consumer_group, topic, partition_offsets, processing_stats, status
) VALUES 
(
    'intelligence-compliance-regulatory-group', 'regulatory.updates', 
    '{"0": 0, "1": 0, "2": 0}', 
    '{"messages_processed": 0, "messages_failed": 0, "avg_processing_time": 0}',
    'active'
),
(
    'intelligence-compliance-regulatory-group', 'regulatory.deadlines', 
    '{"0": 0, "1": 0}', 
    '{"messages_processed": 0, "messages_failed": 0, "avg_processing_time": 0}',
    'active'
),
(
    'intelligence-compliance-regulatory-group', 'regulatory.audit', 
    '{"0": 0, "1": 0, "2": 0, "3": 0}', 
    '{"messages_processed": 0, "messages_failed": 0, "avg_processing_time": 0}',
    'active'
)
ON CONFLICT (consumer_group) DO NOTHING;

-- =============================================================================
-- PHASE 4: COMPLIANCE REPORT GENERATION TABLES
-- =============================================================================

-- Compliance reports metadata and tracking
CREATE TABLE IF NOT EXISTS compliance_reports (
    report_id VARCHAR(100) PRIMARY KEY,
    report_type VARCHAR(50) NOT NULL, -- FINREP, COREP, DORA_ICT
    report_format VARCHAR(20) NOT NULL, -- XBRL, CSV, JSON
    institution_id VARCHAR(50) NOT NULL,
    reporting_period VARCHAR(20) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    template_version VARCHAR(20) NOT NULL,
    file_path TEXT,
    file_size BIGINT,
    checksum VARCHAR(64),
    status VARCHAR(30) DEFAULT 'PENDING', -- PENDING, GENERATING, COMPLETED, FAILED, DELIVERED
    priority INTEGER DEFAULT 2, -- 1=High, 2=Medium, 3=Low
    deadline TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB
);

-- Report generation status tracking
CREATE TABLE IF NOT EXISTS report_generation_status (
    report_id VARCHAR(100) PRIMARY KEY REFERENCES compliance_reports(report_id),
    status VARCHAR(30) NOT NULL,
    progress_percentage INTEGER DEFAULT 0,
    current_step VARCHAR(100),
    steps_completed INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    generation_time_ms INTEGER,
    validation_results JSONB,
    error_message TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Institution configuration for reporting
CREATE TABLE IF NOT EXISTS institutions (
    institution_id VARCHAR(50) PRIMARY KEY,
    institution_code VARCHAR(20) NOT NULL UNIQUE,
    institution_name VARCHAR(200) NOT NULL,
    lei_code VARCHAR(20),
    jurisdiction VARCHAR(10) NOT NULL,
    primary_currency VARCHAR(3) DEFAULT 'EUR',
    consolidation_basis VARCHAR(30) DEFAULT 'Individual',
    reporting_frequency JSONB, -- Frequency by report type
    delivery_preferences JSONB, -- Delivery preferences by report type
    contact_information JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- FINREP specific data tables
CREATE TABLE IF NOT EXISTS finrep_data (
    data_id VARCHAR(100) PRIMARY KEY,
    institution_id VARCHAR(50) NOT NULL REFERENCES institutions(institution_id),
    reporting_period VARCHAR(20) NOT NULL,
    consolidation_basis VARCHAR(30) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    
    -- Balance Sheet - Assets
    cash_balances DECIMAL(15,2) DEFAULT 0,
    financial_assets_hft DECIMAL(15,2) DEFAULT 0,
    financial_assets_mandatorily_fvtpl DECIMAL(15,2) DEFAULT 0,
    financial_assets_designated_fvtpl DECIMAL(15,2) DEFAULT 0,
    financial_assets_fvoci DECIMAL(15,2) DEFAULT 0,
    financial_assets_amortised_cost DECIMAL(15,2) DEFAULT 0,
    derivatives_hedge_accounting DECIMAL(15,2) DEFAULT 0,
    investments_subsidiaries DECIMAL(15,2) DEFAULT 0,
    tangible_assets DECIMAL(15,2) DEFAULT 0,
    intangible_assets DECIMAL(15,2) DEFAULT 0,
    tax_assets DECIMAL(15,2) DEFAULT 0,
    other_assets DECIMAL(15,2) DEFAULT 0,
    total_assets DECIMAL(15,2) NOT NULL,
    
    -- Balance Sheet - Liabilities
    financial_liabilities_hft DECIMAL(15,2) DEFAULT 0,
    financial_liabilities_designated_fvtpl DECIMAL(15,2) DEFAULT 0,
    financial_liabilities_amortised_cost DECIMAL(15,2) DEFAULT 0,
    derivatives_hedge_accounting_liab DECIMAL(15,2) DEFAULT 0,
    provisions DECIMAL(15,2) DEFAULT 0,
    tax_liabilities DECIMAL(15,2) DEFAULT 0,
    other_liabilities DECIMAL(15,2) DEFAULT 0,
    total_liabilities DECIMAL(15,2) NOT NULL,
    
    -- Balance Sheet - Equity
    capital DECIMAL(15,2) DEFAULT 0,
    retained_earnings DECIMAL(15,2) DEFAULT 0,
    accumulated_oci DECIMAL(15,2) DEFAULT 0,
    other_reserves DECIMAL(15,2) DEFAULT 0,
    total_equity DECIMAL(15,2) NOT NULL,
    
    -- P&L Statement
    interest_income DECIMAL(15,2) DEFAULT 0,
    interest_expenses DECIMAL(15,2) DEFAULT 0,
    net_interest_income DECIMAL(15,2) DEFAULT 0,
    fee_income DECIMAL(15,2) DEFAULT 0,
    fee_expenses DECIMAL(15,2) DEFAULT 0,
    net_fee_income DECIMAL(15,2) DEFAULT 0,
    trading_income DECIMAL(15,2) DEFAULT 0,
    other_operating_income DECIMAL(15,2) DEFAULT 0,
    total_operating_income DECIMAL(15,2) DEFAULT 0,
    staff_expenses DECIMAL(15,2) DEFAULT 0,
    other_administrative_expenses DECIMAL(15,2) DEFAULT 0,
    depreciation DECIMAL(15,2) DEFAULT 0,
    total_operating_expenses DECIMAL(15,2) DEFAULT 0,
    impairment_losses DECIMAL(15,2) DEFAULT 0,
    profit_before_tax DECIMAL(15,2) DEFAULT 0,
    tax_expense DECIMAL(15,2) DEFAULT 0,
    net_profit DECIMAL(15,2) DEFAULT 0,
    
    data_source VARCHAR(100),
    data_quality_score DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Phase 4 tables
CREATE INDEX IF NOT EXISTS idx_compliance_reports_type_period ON compliance_reports (report_type, reporting_period);
CREATE INDEX IF NOT EXISTS idx_compliance_reports_institution ON compliance_reports (institution_id);
CREATE INDEX IF NOT EXISTS idx_compliance_reports_status ON compliance_reports (status);
CREATE INDEX IF NOT EXISTS idx_compliance_reports_deadline ON compliance_reports (deadline);

CREATE INDEX IF NOT EXISTS idx_institutions_code ON institutions (institution_code);
CREATE INDEX IF NOT EXISTS idx_institutions_jurisdiction ON institutions (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_institutions_active ON institutions (is_active);

CREATE INDEX IF NOT EXISTS idx_finrep_data_institution_period ON finrep_data (institution_id, reporting_period);
CREATE INDEX IF NOT EXISTS idx_finrep_data_created_at ON finrep_data (created_at);

-- Triggers for updated_at columns on Phase 4 tables
CREATE TRIGGER update_compliance_reports_updated_at BEFORE UPDATE ON compliance_reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_report_generation_status_updated_at BEFORE UPDATE ON report_generation_status FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_institutions_updated_at BEFORE UPDATE ON institutions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_finrep_data_updated_at BEFORE UPDATE ON finrep_data FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default data for Phase 4

-- Default institutions
INSERT INTO institutions (institution_id, institution_code, institution_name, jurisdiction, primary_currency, consolidation_basis) VALUES
('INST_001', 'TESTBANK001', 'Test Bank AG', 'DE', 'EUR', 'Individual'),
('INST_002', 'TESTBANK002', 'Test Credit Union Ltd', 'IE', 'EUR', 'Consolidated'),
('INST_003', 'TESTBANK003', 'Test Investment Bank PLC', 'GB', 'GBP', 'Individual')
ON CONFLICT (institution_id) DO NOTHING;

-- Sample FINREP data for testing
INSERT INTO finrep_data (
    data_id, institution_id, reporting_period, consolidation_basis, currency,
    cash_balances, financial_assets_amortised_cost, total_assets,
    financial_liabilities_amortised_cost, total_liabilities,
    capital, retained_earnings, total_equity,
    interest_income, interest_expenses, net_interest_income,
    staff_expenses, total_operating_expenses, net_profit
) VALUES (
    'FINREP_001_2024Q1', 'INST_001', '2024-Q1', 'Individual', 'EUR',
    50000000.00, 800000000.00, 1000000000.00,
    750000000.00, 800000000.00,
    150000000.00, 50000000.00, 200000000.00,
    25000000.00, 8000000.00, 17000000.00,
    12000000.00, 20000000.00, 8000000.00
) ON CONFLICT (data_id) DO NOTHING;

-- =============================================================================
-- PHASE 4 ADDITIONAL TABLES - SLA MONITORING AND PERFORMANCE TRACKING
-- =============================================================================

-- Delivery tracking tables
CREATE TABLE IF NOT EXISTS delivery_tracking (
    tracking_id VARCHAR(50) PRIMARY KEY,
    report_id VARCHAR(100) NOT NULL,
    delivery_channel VARCHAR(50) NOT NULL,
    destination VARCHAR(500) NOT NULL,
    delivery_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP WITH TIME ZONE,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    confirmation_receipt TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS delivery_confirmations (
    confirmation_id VARCHAR(50) PRIMARY KEY,
    tracking_id VARCHAR(50) NOT NULL REFERENCES delivery_tracking(tracking_id),
    confirmed_by VARCHAR(200) NOT NULL,
    confirmation_method VARCHAR(100) NOT NULL,
    confirmation_data JSONB DEFAULT '{}',
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    verified BOOLEAN DEFAULT FALSE,
    verification_signature VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS delivery_alerts (
    alert_id VARCHAR(50) PRIMARY KEY,
    tracking_id VARCHAR(50) NOT NULL REFERENCES delivery_tracking(tracking_id),
    alert_level VARCHAR(50) NOT NULL,
    alert_type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    escalated BOOLEAN DEFAULT FALSE,
    escalation_level INTEGER DEFAULT 0
);

-- SLA monitoring tables
CREATE TABLE IF NOT EXISTS sla_definitions (
    sla_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    service_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    threshold_value DECIMAL(10,3) NOT NULL,
    threshold_operator VARCHAR(10) NOT NULL,
    time_window VARCHAR(20) NOT NULL,
    evaluation_frequency INTEGER NOT NULL,
    breach_threshold DECIMAL(5,2) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    tags JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sla_measurements (
    measurement_id VARCHAR(50) PRIMARY KEY,
    sla_id VARCHAR(50),
    service_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    value DECIMAL(15,6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    labels JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS sla_violations (
    violation_id VARCHAR(50) PRIMARY KEY,
    sla_id VARCHAR(50) NOT NULL REFERENCES sla_definitions(sla_id),
    service_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    threshold_value DECIMAL(10,3) NOT NULL,
    actual_value DECIMAL(15,6) NOT NULL,
    violation_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    violation_end TIMESTAMP WITH TIME ZONE,
    duration_seconds DECIMAL(10,3),
    severity VARCHAR(50) NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    root_cause TEXT,
    resolution_notes TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Performance tracking tables
CREATE TABLE IF NOT EXISTS performance_metric_definitions (
    metric_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    metric_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    labels JSONB DEFAULT '[]',
    unit VARCHAR(50),
    alert_thresholds JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    retention_days INTEGER DEFAULT 30,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS performance_metrics (
    metric_id VARCHAR(50) PRIMARY KEY,
    metric_name VARCHAR(200) NOT NULL,
    value TEXT NOT NULL,
    labels JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS performance_alerts (
    alert_id VARCHAR(50) PRIMARY KEY,
    metric_id VARCHAR(50) NOT NULL,
    metric_name VARCHAR(200) NOT NULL,
    threshold_type VARCHAR(50) NOT NULL,
    threshold_value DECIMAL(15,6) NOT NULL,
    actual_value DECIMAL(15,6) NOT NULL,
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- SLA alerting tables
CREATE TABLE IF NOT EXISTS sla_escalation_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    escalation_levels JSONB NOT NULL,
    max_escalation_level INTEGER NOT NULL,
    auto_escalation_enabled BOOLEAN DEFAULT TRUE,
    business_hours_only BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sla_alert_recipients (
    recipient_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    role VARCHAR(100) NOT NULL,
    escalation_level INTEGER NOT NULL,
    contact_methods JSONB NOT NULL,
    availability_schedule JSONB DEFAULT '{}',
    notification_preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sla_incidents (
    incident_id VARCHAR(50) PRIMARY KEY,
    violation_id VARCHAR(50) NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    escalation_level INTEGER DEFAULT 0,
    escalated_at TIMESTAMP WITH TIME ZONE,
    root_cause TEXT,
    recovery_actions_taken JSONB DEFAULT '[]',
    impact_assessment JSONB DEFAULT '{}',
    resolution_notes TEXT,
    post_incident_review TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS sla_alert_notifications (
    notification_id VARCHAR(50) PRIMARY KEY,
    incident_id VARCHAR(50) NOT NULL REFERENCES sla_incidents(incident_id),
    recipient_id VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    escalation_level INTEGER NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS sla_recovery_actions (
    action_id VARCHAR(50) PRIMARY KEY,
    incident_id VARCHAR(50) NOT NULL REFERENCES sla_incidents(incident_id),
    action_type VARCHAR(100) NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL,
    execution_time_seconds DECIMAL(10,3),
    result_data JSONB DEFAULT '{}',
    error_message TEXT
);

-- Scheduling tables
CREATE TABLE IF NOT EXISTS report_schedules (
    schedule_id VARCHAR(50) PRIMARY KEY,
    report_type VARCHAR(100) NOT NULL,
    institution_id VARCHAR(50) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    cron_expression VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 2,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    next_run_time TIMESTAMP WITH TIME ZONE,
    last_run_time TIMESTAMP WITH TIME ZONE,
    dependencies JSONB DEFAULT '[]',
    max_retries INTEGER DEFAULT 3,
    retry_delay_minutes INTEGER DEFAULT 30,
    timeout_minutes INTEGER DEFAULT 120,
    resource_requirements JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    job_id VARCHAR(50) PRIMARY KEY,
    schedule_id VARCHAR(50) NOT NULL REFERENCES report_schedules(schedule_id),
    report_type VARCHAR(100) NOT NULL,
    institution_id VARCHAR(50) NOT NULL,
    reporting_period VARCHAR(50) NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    started_time TIMESTAMP WITH TIME ZONE,
    completed_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'SCHEDULED',
    priority INTEGER DEFAULT 2,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    result_data JSONB DEFAULT '{}',
    resource_allocation JSONB DEFAULT '{}',
    dependencies_met BOOLEAN DEFAULT FALSE,
    dependency_jobs JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Deadline management tables
CREATE TABLE IF NOT EXISTS regulatory_deadlines (
    deadline_id VARCHAR(50) PRIMARY KEY,
    report_type VARCHAR(100) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    frequency VARCHAR(50) NOT NULL,
    deadline_type VARCHAR(50) NOT NULL,
    business_days_offset INTEGER DEFAULT 0,
    calendar_days_offset INTEGER DEFAULT 0,
    description TEXT,
    regulatory_reference VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    dependencies JSONB DEFAULT '[]',
    lead_time_days INTEGER DEFAULT 0,
    review_time_days INTEGER DEFAULT 0,
    buffer_days INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS calculated_deadlines (
    calculation_id VARCHAR(50) PRIMARY KEY,
    deadline_id VARCHAR(50) NOT NULL REFERENCES regulatory_deadlines(deadline_id),
    report_id VARCHAR(100) NOT NULL,
    reporting_period VARCHAR(50) NOT NULL,
    calculated_date DATE NOT NULL,
    preparation_start_date DATE NOT NULL,
    review_start_date DATE NOT NULL,
    final_deadline DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'UPCOMING',
    days_remaining INTEGER,
    business_days_remaining INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    dependencies_met BOOLEAN DEFAULT FALSE,
    dependency_status JSONB DEFAULT '{}',
    alerts_sent JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Alert management tables
CREATE TABLE IF NOT EXISTS deadline_alert_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    rule_name VARCHAR(200) NOT NULL,
    report_type VARCHAR(100) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    trigger_conditions JSONB NOT NULL,
    channels JSONB NOT NULL,
    severity VARCHAR(50) NOT NULL,
    escalation_enabled BOOLEAN DEFAULT TRUE,
    escalation_delay_minutes INTEGER DEFAULT 60,
    max_escalation_level INTEGER DEFAULT 2,
    template_name VARCHAR(100) DEFAULT 'default_deadline_alert',
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notification_recipients (
    recipient_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL,
    phone VARCHAR(50),
    role VARCHAR(100) NOT NULL,
    escalation_level INTEGER DEFAULT 0,
    channels JSONB DEFAULT '[]',
    timezone VARCHAR(50) DEFAULT 'UTC',
    notification_preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deadline_alerts (
    alert_id VARCHAR(50) PRIMARY KEY,
    rule_id VARCHAR(50) NOT NULL REFERENCES deadline_alert_rules(rule_id),
    deadline_calculation_id VARCHAR(50) NOT NULL REFERENCES calculated_deadlines(calculation_id),
    report_type VARCHAR(100) NOT NULL,
    institution_id VARCHAR(50) NOT NULL,
    reporting_period VARCHAR(50) NOT NULL,
    deadline_date TIMESTAMP WITH TIME ZONE NOT NULL,
    days_remaining INTEGER NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    triggered_by VARCHAR(100) DEFAULT 'system',
    escalation_level INTEGER DEFAULT 0,
    escalated_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS notification_instances (
    notification_id VARCHAR(50) PRIMARY KEY,
    alert_id VARCHAR(50) NOT NULL REFERENCES deadline_alerts(alert_id),
    recipient_id VARCHAR(50) NOT NULL REFERENCES notification_recipients(recipient_id),
    channel VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS ui_notifications (
    notification_id VARCHAR(50) PRIMARY KEY,
    recipient_id VARCHAR(50) NOT NULL,
    alert_id VARCHAR(50),
    title VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- EBA API tracking tables
CREATE TABLE IF NOT EXISTS eba_submissions (
    submission_id VARCHAR(50) PRIMARY KEY,
    report_id VARCHAR(100) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    institution_lei VARCHAR(20) NOT NULL,
    reporting_period VARCHAR(50) NOT NULL,
    submission_status VARCHAR(50) DEFAULT 'PENDING',
    eba_reference VARCHAR(100),
    submitted_at TIMESTAMP WITH TIME ZONE,
    accepted_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trend analysis tables
CREATE TABLE IF NOT EXISTS sla_trend_analysis (
    analysis_id VARCHAR(50) PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    trend_direction VARCHAR(50) NOT NULL,
    analysis_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    analysis_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    data_points_count INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- =============================================================================
-- INDEXES FOR PHASE 4 ADDITIONAL TABLES
-- =============================================================================

-- Delivery tracking indexes
CREATE INDEX IF NOT EXISTS idx_delivery_tracking_report_id ON delivery_tracking(report_id);
CREATE INDEX IF NOT EXISTS idx_delivery_tracking_status ON delivery_tracking(delivery_status);
CREATE INDEX IF NOT EXISTS idx_delivery_tracking_channel ON delivery_tracking(delivery_channel);
CREATE INDEX IF NOT EXISTS idx_delivery_tracking_created_at ON delivery_tracking(created_at);

-- SLA monitoring indexes
CREATE INDEX IF NOT EXISTS idx_sla_definitions_service ON sla_definitions(service_name);
CREATE INDEX IF NOT EXISTS idx_sla_definitions_active ON sla_definitions(is_active);
CREATE INDEX IF NOT EXISTS idx_sla_measurements_service_type ON sla_measurements(service_name, metric_type);
CREATE INDEX IF NOT EXISTS idx_sla_measurements_timestamp ON sla_measurements(timestamp);
CREATE INDEX IF NOT EXISTS idx_sla_violations_service ON sla_violations(service_name);
CREATE INDEX IF NOT EXISTS idx_sla_violations_resolved ON sla_violations(resolved);

-- Performance tracking indexes
CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON performance_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_alerts_metric ON performance_alerts(metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_alerts_triggered ON performance_alerts(triggered_at);

-- Scheduling indexes
CREATE INDEX IF NOT EXISTS idx_report_schedules_type ON report_schedules(report_type);
CREATE INDEX IF NOT EXISTS idx_report_schedules_status ON report_schedules(status);
CREATE INDEX IF NOT EXISTS idx_report_schedules_next_run ON report_schedules(next_run_time);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_status ON scheduled_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_scheduled_time ON scheduled_jobs(scheduled_time);

-- Deadline management indexes
CREATE INDEX IF NOT EXISTS idx_regulatory_deadlines_type ON regulatory_deadlines(report_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_deadlines_jurisdiction ON regulatory_deadlines(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_calculated_deadlines_report ON calculated_deadlines(report_id);
CREATE INDEX IF NOT EXISTS idx_calculated_deadlines_status ON calculated_deadlines(status);
CREATE INDEX IF NOT EXISTS idx_calculated_deadlines_final_deadline ON calculated_deadlines(final_deadline);

-- Alert management indexes
CREATE INDEX IF NOT EXISTS idx_deadline_alerts_report_type ON deadline_alerts(report_type);
CREATE INDEX IF NOT EXISTS idx_deadline_alerts_severity ON deadline_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_deadline_alerts_created_at ON deadline_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_notification_instances_status ON notification_instances(status);
CREATE INDEX IF NOT EXISTS idx_ui_notifications_recipient ON ui_notifications(recipient_id);
CREATE INDEX IF NOT EXISTS idx_ui_notifications_read ON ui_notifications(is_read);

-- =============================================================================
-- TRIGGERS FOR PHASE 4 ADDITIONAL TABLES
-- =============================================================================

-- Delivery tracking triggers
CREATE TRIGGER update_delivery_tracking_updated_at BEFORE UPDATE ON delivery_tracking FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- SLA monitoring triggers
CREATE TRIGGER update_sla_definitions_updated_at BEFORE UPDATE ON sla_definitions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Performance tracking triggers
CREATE TRIGGER update_performance_metric_definitions_updated_at BEFORE UPDATE ON performance_metric_definitions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Scheduling triggers
CREATE TRIGGER update_report_schedules_updated_at BEFORE UPDATE ON report_schedules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_scheduled_jobs_updated_at BEFORE UPDATE ON scheduled_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Deadline management triggers
CREATE TRIGGER update_regulatory_deadlines_updated_at BEFORE UPDATE ON regulatory_deadlines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_calculated_deadlines_updated_at BEFORE UPDATE ON calculated_deadlines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Alert management triggers
CREATE TRIGGER update_deadline_alert_rules_updated_at BEFORE UPDATE ON deadline_alert_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_notification_recipients_updated_at BEFORE UPDATE ON notification_recipients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sla_escalation_rules_updated_at BEFORE UPDATE ON sla_escalation_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sla_alert_recipients_updated_at BEFORE UPDATE ON sla_alert_recipients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_eba_submissions_updated_at BEFORE UPDATE ON eba_submissions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Schema version update
-- Schema version: 4.4.0 (Phase 4: Complete Implementation with SLA Monitoring)
-- Last updated: Phase 4 Complete - All components implemented with full @rules.mdc compliance
