-- KYC Automation Platform Database Schema
-- This file contains the complete database schema for the KYC automation platform
-- It includes all tables required for storing KYC processing data, audit trails, and system metadata

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for encryption functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Customers table for storing customer information
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(255) UNIQUE,
    email VARCHAR(255),
    phone VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- KYC requests table for tracking all verification requests
CREATE TABLE kyc_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id VARCHAR(255) UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    processing_config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexes for performance
    INDEX idx_kyc_requests_request_id (request_id),
    INDEX idx_kyc_requests_customer_id (customer_id),
    INDEX idx_kyc_requests_status (status),
    INDEX idx_kyc_requests_created_at (created_at)
);

-- Documents table for storing uploaded document information
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kyc_request_id UUID REFERENCES kyc_requests(id) ON DELETE CASCADE,
    document_type VARCHAR(100) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    checksum VARCHAR(64), -- SHA-256 checksum for integrity
    encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_documents_kyc_request_id (kyc_request_id),
    INDEX idx_documents_document_type (document_type),
    INDEX idx_documents_created_at (created_at)
);

-- KYC results table for storing final processing results
CREATE TABLE kyc_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kyc_request_id UUID REFERENCES kyc_requests(id) ON DELETE CASCADE,
    request_id VARCHAR(255) NOT NULL,
    recommendation VARCHAR(50) NOT NULL, -- APPROVE, CONDITIONAL, ESCALATE, REJECT
    risk_score DECIMAL(5,2) NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    cost_savings DECIMAL(10,2),
    executive_summary JSONB NOT NULL DEFAULT '{}',
    detailed_analysis JSONB NOT NULL DEFAULT '{}',
    audit_trail JSONB NOT NULL DEFAULT '{}',
    actionable_insights JSONB NOT NULL DEFAULT '{}',
    qa_verdict JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_kyc_results_kyc_request_id (kyc_request_id),
    INDEX idx_kyc_results_request_id (request_id),
    INDEX idx_kyc_results_recommendation (recommendation),
    INDEX idx_kyc_results_risk_score (risk_score),
    INDEX idx_kyc_results_created_at (created_at)
);

-- =============================================================================
-- AGENT PROCESSING TABLES
-- =============================================================================

-- OCR results table for storing OCR processing results
CREATE TABLE ocr_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kyc_request_id UUID REFERENCES kyc_requests(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    extracted_text TEXT,
    extracted_data JSONB NOT NULL DEFAULT '{}',
    confidence_score DECIMAL(5,2) NOT NULL,
    document_quality DECIMAL(5,2) NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    errors TEXT[],
    warnings TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_ocr_results_kyc_request_id (kyc_request_id),
    INDEX idx_ocr_results_document_id (document_id),
    INDEX idx_ocr_results_confidence_score (confidence_score),
    INDEX idx_ocr_results_created_at (created_at)
);

-- Face recognition results table
CREATE TABLE face_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kyc_request_id UUID REFERENCES kyc_requests(id) ON DELETE CASCADE,
    selfie_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    id_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    match_score DECIMAL(5,2),
    is_match BOOLEAN,
    liveness_detected BOOLEAN,
    liveness_confidence DECIMAL(5,2),
    overall_score DECIMAL(5,2) NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    selfie_analysis JSONB DEFAULT '{}',
    id_photo_analysis JSONB DEFAULT '{}',
    liveness_result JSONB DEFAULT '{}',
    matching_result JSONB DEFAULT '{}',
    errors TEXT[],
    warnings TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_face_results_kyc_request_id (kyc_request_id),
    INDEX idx_face_results_match_score (match_score),
    INDEX idx_face_results_is_match (is_match),
    INDEX idx_face_results_created_at (created_at)
);

-- Watchlist screening results table
CREATE TABLE watchlist_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kyc_request_id UUID REFERENCES kyc_requests(id) ON DELETE CASCADE,
    flagged BOOLEAN NOT NULL DEFAULT false,
    total_matches INTEGER NOT NULL DEFAULT 0,
    highest_risk_level VARCHAR(50),
    overall_confidence DECIMAL(5,2) NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    lists_checked TEXT[],
    matches JSONB DEFAULT '[]',
    errors TEXT[],
    warnings TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_watchlist_results_kyc_request_id (kyc_request_id),
    INDEX idx_watchlist_results_flagged (flagged),
    INDEX idx_watchlist_results_highest_risk_level (highest_risk_level),
    INDEX idx_watchlist_results_created_at (created_at)
);

-- Data integration results table
CREATE TABLE data_integration_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kyc_request_id UUID REFERENCES kyc_requests(id) ON DELETE CASCADE,
    overall_risk_score DECIMAL(5,2) NOT NULL,
    data_completeness_score DECIMAL(5,2) NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    email_verification JSONB DEFAULT '{}',
    phone_verification JSONB DEFAULT '{}',
    credit_bureau_data JSONB DEFAULT '{}',
    social_media_profiles JSONB DEFAULT '[]',
    address_verification JSONB DEFAULT '{}',
    public_records JSONB DEFAULT '{}',
    errors TEXT[],
    warnings TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_data_integration_results_kyc_request_id (kyc_request_id),
    INDEX idx_data_integration_results_overall_risk_score (overall_risk_score),
    INDEX idx_data_integration_results_created_at (created_at)
);

-- Quality assurance results table
CREATE TABLE qa_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kyc_request_id UUID REFERENCES kyc_requests(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL, -- passed, failed, warning, manual_review
    qa_score DECIMAL(5,2) NOT NULL,
    requires_manual_review BOOLEAN NOT NULL DEFAULT false,
    processing_time_ms INTEGER NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}',
    validation_rules JSONB DEFAULT '[]',
    exceptions JSONB DEFAULT '[]',
    recommendations TEXT[],
    errors TEXT[],
    warnings TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_qa_results_kyc_request_id (kyc_request_id),
    INDEX idx_qa_results_status (status),
    INDEX idx_qa_results_qa_score (qa_score),
    INDEX idx_qa_results_requires_manual_review (requires_manual_review),
    INDEX idx_qa_results_created_at (created_at)
);

-- =============================================================================
-- FEEDBACK AND LEARNING TABLES
-- =============================================================================

-- Feedback table for continuous learning
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kyc_request_id UUID REFERENCES kyc_requests(id) ON DELETE CASCADE,
    reviewer_id VARCHAR(255) NOT NULL,
    feedback_type VARCHAR(50) NOT NULL, -- correction, confirmation, improvement, issue
    feedback_text TEXT NOT NULL,
    corrections JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    INDEX idx_feedback_kyc_request_id (kyc_request_id),
    INDEX idx_feedback_reviewer_id (reviewer_id),
    INDEX idx_feedback_feedback_type (feedback_type),
    INDEX idx_feedback_processed (processed),
    INDEX idx_feedback_created_at (created_at)
);

-- =============================================================================
-- AUDIT AND COMPLIANCE TABLES
-- =============================================================================

-- Audit log table for compliance and tracking
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kyc_request_id UUID REFERENCES kyc_requests(id) ON DELETE SET NULL,
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_audit_log_kyc_request_id (kyc_request_id),
    INDEX idx_audit_log_user_id (user_id),
    INDEX idx_audit_log_action (action),
    INDEX idx_audit_log_resource_type (resource_type),
    INDEX idx_audit_log_created_at (created_at)
);

-- Data retention tracking table
CREATE TABLE data_retention (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    retention_policy VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    INDEX idx_data_retention_table_name (table_name),
    INDEX idx_data_retention_expires_at (expires_at),
    INDEX idx_data_retention_deleted_at (deleted_at)
);

-- =============================================================================
-- SYSTEM AND CONFIGURATION TABLES
-- =============================================================================

-- System configuration table
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_system_config_config_key (config_key)
);

-- Agent health status table
CREATE TABLE agent_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL, -- healthy, unhealthy, unknown
    last_check TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Indexes
    INDEX idx_agent_health_agent_name (agent_name),
    INDEX idx_agent_health_status (status),
    INDEX idx_agent_health_last_check (last_check)
);

-- Processing metrics table
CREATE TABLE processing_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4) NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- counter, gauge, histogram
    labels JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_processing_metrics_metric_name (metric_name),
    INDEX idx_processing_metrics_timestamp (timestamp)
);

-- =============================================================================
-- WATCHLIST DATA TABLES
-- =============================================================================

-- Sanctions watchlist table
CREATE TABLE sanctions_watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    aliases TEXT[],
    date_of_birth DATE,
    nationality VARCHAR(100),
    list_type VARCHAR(100) NOT NULL,
    program VARCHAR(200) NOT NULL,
    added_date DATE NOT NULL,
    removed_date DATE,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_sanctions_watchlist_name (name),
    INDEX idx_sanctions_watchlist_list_type (list_type),
    INDEX idx_sanctions_watchlist_is_active (is_active),
    INDEX idx_sanctions_watchlist_added_date (added_date)
);

-- PEP (Politically Exposed Persons) watchlist table
CREATE TABLE pep_watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    aliases TEXT[],
    date_of_birth DATE,
    nationality VARCHAR(100),
    position VARCHAR(500),
    country VARCHAR(100),
    risk_level VARCHAR(50) DEFAULT 'medium',
    added_date DATE NOT NULL,
    removed_date DATE,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_pep_watchlist_name (name),
    INDEX idx_pep_watchlist_country (country),
    INDEX idx_pep_watchlist_risk_level (risk_level),
    INDEX idx_pep_watchlist_is_active (is_active)
);

-- Adverse media watchlist table
CREATE TABLE adverse_media_watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    aliases TEXT[],
    date_of_birth DATE,
    nationality VARCHAR(100),
    category VARCHAR(200) NOT NULL,
    source VARCHAR(500) NOT NULL,
    severity VARCHAR(50) DEFAULT 'medium',
    added_date DATE NOT NULL,
    removed_date DATE,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_adverse_media_watchlist_name (name),
    INDEX idx_adverse_media_watchlist_category (category),
    INDEX idx_adverse_media_watchlist_severity (severity),
    INDEX idx_adverse_media_watchlist_is_active (is_active)
);

-- =============================================================================
-- VIEWS FOR REPORTING AND ANALYTICS
-- =============================================================================

-- KYC processing summary view
CREATE VIEW kyc_processing_summary AS
SELECT 
    kr.id,
    kr.request_id,
    kr.status,
    kr.created_at,
    kr.completed_at,
    kres.recommendation,
    kres.risk_score,
    kres.confidence,
    kres.processing_time_ms,
    c.customer_id,
    c.email,
    COUNT(d.id) as document_count,
    CASE 
        WHEN kr.completed_at IS NOT NULL THEN 
            EXTRACT(EPOCH FROM (kr.completed_at - kr.created_at)) * 1000
        ELSE NULL 
    END as total_processing_time_ms
FROM kyc_requests kr
LEFT JOIN customers c ON kr.customer_id = c.id
LEFT JOIN kyc_results kres ON kr.id = kres.kyc_request_id
LEFT JOIN documents d ON kr.id = d.kyc_request_id
GROUP BY kr.id, kr.request_id, kr.status, kr.created_at, kr.completed_at, 
         kres.recommendation, kres.risk_score, kres.confidence, kres.processing_time_ms,
         c.customer_id, c.email;

-- Agent performance view
CREATE VIEW agent_performance AS
SELECT 
    'ocr' as agent_name,
    COUNT(*) as total_requests,
    AVG(confidence_score) as avg_confidence,
    AVG(processing_time_ms) as avg_processing_time,
    COUNT(CASE WHEN array_length(errors, 1) > 0 THEN 1 END) as error_count
FROM ocr_results
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
UNION ALL
SELECT 
    'face' as agent_name,
    COUNT(*) as total_requests,
    AVG(overall_score) as avg_confidence,
    AVG(processing_time_ms) as avg_processing_time,
    COUNT(CASE WHEN array_length(errors, 1) > 0 THEN 1 END) as error_count
FROM face_results
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
UNION ALL
SELECT 
    'watchlist' as agent_name,
    COUNT(*) as total_requests,
    AVG(overall_confidence) as avg_confidence,
    AVG(processing_time_ms) as avg_processing_time,
    COUNT(CASE WHEN array_length(errors, 1) > 0 THEN 1 END) as error_count
FROM watchlist_results
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
UNION ALL
SELECT 
    'data_integration' as agent_name,
    COUNT(*) as total_requests,
    AVG(data_completeness_score) as avg_confidence,
    AVG(processing_time_ms) as avg_processing_time,
    COUNT(CASE WHEN array_length(errors, 1) > 0 THEN 1 END) as error_count
FROM data_integration_results
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
UNION ALL
SELECT 
    'qa' as agent_name,
    COUNT(*) as total_requests,
    AVG(qa_score) as avg_confidence,
    AVG(processing_time_ms) as avg_processing_time,
    COUNT(CASE WHEN array_length(errors, 1) > 0 THEN 1 END) as error_count
FROM qa_results
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';

-- =============================================================================
-- FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at columns
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kyc_requests_updated_at BEFORE UPDATE ON kyc_requests 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically create data retention records
CREATE OR REPLACE FUNCTION create_data_retention_record()
RETURNS TRIGGER AS $$
BEGIN
    -- Documents retention (7 years)
    IF TG_TABLE_NAME = 'documents' THEN
        INSERT INTO data_retention (table_name, record_id, retention_policy, created_at, expires_at)
        VALUES ('documents', NEW.id, 'documents_7_years', NEW.created_at, NEW.created_at + INTERVAL '7 years');
    END IF;
    
    -- KYC results retention (7 years)
    IF TG_TABLE_NAME = 'kyc_results' THEN
        INSERT INTO data_retention (table_name, record_id, retention_policy, created_at, expires_at)
        VALUES ('kyc_results', NEW.id, 'results_7_years', NEW.created_at, NEW.created_at + INTERVAL '7 years');
    END IF;
    
    -- Audit log retention (3 years)
    IF TG_TABLE_NAME = 'audit_log' THEN
        INSERT INTO data_retention (table_name, record_id, retention_policy, created_at, expires_at)
        VALUES ('audit_log', NEW.id, 'audit_3_years', NEW.created_at, NEW.created_at + INTERVAL '3 years');
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for data retention
CREATE TRIGGER create_documents_retention AFTER INSERT ON documents 
    FOR EACH ROW EXECUTE FUNCTION create_data_retention_record();

CREATE TRIGGER create_kyc_results_retention AFTER INSERT ON kyc_results 
    FOR EACH ROW EXECUTE FUNCTION create_data_retention_record();

CREATE TRIGGER create_audit_log_retention AFTER INSERT ON audit_log 
    FOR EACH ROW EXECUTE FUNCTION create_data_retention_record();

-- =============================================================================
-- INITIAL DATA AND CONFIGURATION
-- =============================================================================

-- Insert default system configuration
INSERT INTO system_config (config_key, config_value, description) VALUES
('platform_version', '"1.0.0"', 'Current platform version'),
('maintenance_mode', 'false', 'Enable/disable maintenance mode'),
('max_concurrent_requests', '100', 'Maximum concurrent KYC requests'),
('default_risk_tolerance', '"medium"', 'Default risk tolerance level'),
('enable_audit_logging', 'true', 'Enable comprehensive audit logging'),
('data_encryption_enabled', 'true', 'Enable data encryption at rest'),
('session_timeout_hours', '24', 'Default session timeout in hours'),
('max_file_size_mb', '10', 'Maximum file upload size in MB'),
('supported_file_types', '["jpg", "jpeg", "png", "pdf", "tiff", "bmp"]', 'Supported file types for upload'),
('quality_thresholds', '{"min_ocr_confidence": 50.0, "min_face_match": 75.0, "min_document_quality": 60.0}', 'Quality thresholds for processing');

-- Insert sample watchlist data (for development/testing)
INSERT INTO sanctions_watchlist (name, aliases, date_of_birth, nationality, list_type, program, added_date) VALUES
('JOHN DOE SMITH', ARRAY['JOHN D SMITH', 'J D SMITH'], '1970-01-15', 'US', 'sanctions', 'OFAC SDN', '2020-01-01'),
('MARIA GONZALEZ RODRIGUEZ', ARRAY['MARIA G RODRIGUEZ', 'M GONZALEZ'], '1965-03-22', 'MX', 'sanctions', 'OFAC SDN', '2019-05-15'),
('VLADIMIR PETROV', ARRAY['V PETROV', 'VLADIMIR P'], '1960-12-05', 'RU', 'sanctions', 'EU Sanctions', '2021-02-01');

INSERT INTO pep_watchlist (name, aliases, date_of_birth, nationality, position, country, risk_level, added_date) VALUES
('ROBERT JOHNSON', ARRAY['BOB JOHNSON', 'R JOHNSON'], '1955-07-10', 'US', 'Former Government Official', 'US', 'high', '2018-01-01'),
('ANGELA MUELLER', ARRAY['A MUELLER', 'ANGELA M'], '1962-11-30', 'DE', 'Corporate Executive', 'DE', 'medium', '2019-06-01');

INSERT INTO adverse_media_watchlist (name, aliases, date_of_birth, nationality, category, source, severity, added_date) VALUES
('MICHAEL BROWN', ARRAY['MIKE BROWN', 'M BROWN'], '1975-04-18', 'GB', 'Financial Crime', 'News Media', 'medium', '2022-03-15');

-- Create indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_kyc_requests_composite ON kyc_requests (status, created_at, customer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_composite ON documents (kyc_request_id, document_type, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_composite ON audit_log (action, resource_type, created_at);

-- =============================================================================
-- COMMENTS AND DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE customers IS 'Stores customer information for KYC processing';
COMMENT ON TABLE kyc_requests IS 'Tracks all KYC verification requests and their status';
COMMENT ON TABLE documents IS 'Stores information about uploaded documents';
COMMENT ON TABLE kyc_results IS 'Stores final KYC processing results and recommendations';
COMMENT ON TABLE ocr_results IS 'Stores OCR processing results from document analysis';
COMMENT ON TABLE face_results IS 'Stores face recognition and liveness detection results';
COMMENT ON TABLE watchlist_results IS 'Stores watchlist screening results';
COMMENT ON TABLE data_integration_results IS 'Stores external data integration results';
COMMENT ON TABLE qa_results IS 'Stores quality assurance validation results';
COMMENT ON TABLE feedback IS 'Stores user feedback for continuous learning';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for compliance';
COMMENT ON TABLE data_retention IS 'Tracks data retention policies and expiration dates';
COMMENT ON TABLE system_config IS 'System-wide configuration settings';
COMMENT ON TABLE agent_health IS 'Tracks health status of all processing agents';
COMMENT ON TABLE processing_metrics IS 'Stores system performance and processing metrics';

-- Grant permissions (adjust as needed for your environment)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO kyc_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO kyc_user;
