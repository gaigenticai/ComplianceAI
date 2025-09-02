-- ComplianceAI PostgreSQL Database Migration
-- Version: 001
-- Description: Initial schema creation for ComplianceAI regulatory compliance system
-- Date: 2024-01-15
-- Author: ComplianceAI Development Team

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_buffercache";

-- Create schema for regulatory data
CREATE SCHEMA IF NOT EXISTS regulatory;
COMMENT ON SCHEMA regulatory IS 'Schema for regulatory compliance data and configurations';

-- Migration tracking table
CREATE TABLE IF NOT EXISTS regulatory.migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(100),
    checksum VARCHAR(128),
    success BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE regulatory.migrations IS 'Tracks applied database migrations';

-- Create indexes for migration tracking
CREATE INDEX IF NOT EXISTS idx_migrations_version ON regulatory.migrations(version);
CREATE INDEX IF NOT EXISTS idx_migrations_applied_at ON regulatory.migrations(applied_at);

-- Jurisdiction configurations
CREATE TABLE IF NOT EXISTS regulatory.jurisdiction_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jurisdiction_code VARCHAR(10) NOT NULL UNIQUE,
    jurisdiction_name VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    currency_code VARCHAR(3) NOT NULL,
    reporting_standard VARCHAR(20) NOT NULL,
    consolidation_method VARCHAR(20) NOT NULL DEFAULT 'solo',
    language VARCHAR(5) NOT NULL DEFAULT 'en',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

COMMENT ON TABLE regulatory.jurisdiction_configs IS 'Configuration settings for different regulatory jurisdictions';

-- Customer jurisdiction mappings
CREATE TABLE IF NOT EXISTS regulatory.customer_jurisdictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(50) NOT NULL,
    jurisdiction_code VARCHAR(10) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    FOREIGN KEY (jurisdiction_code) REFERENCES regulatory.jurisdiction_configs(jurisdiction_code)
);

COMMENT ON TABLE regulatory.customer_jurisdictions IS 'Mapping of customers to their applicable jurisdictions';

-- Regulatory obligations
CREATE TABLE IF NOT EXISTS regulatory.regulatory_obligations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    obligation_code VARCHAR(50) NOT NULL UNIQUE,
    obligation_name VARCHAR(200) NOT NULL,
    description TEXT,
    jurisdiction_code VARCHAR(10) NOT NULL,
    report_type VARCHAR(20) NOT NULL,
    frequency VARCHAR(20) NOT NULL,
    deadline_offset_days INTEGER NOT NULL,
    grace_period_days INTEGER NOT NULL DEFAULT 0,
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    FOREIGN KEY (jurisdiction_code) REFERENCES regulatory.jurisdiction_configs(jurisdiction_code)
);

COMMENT ON TABLE regulatory.regulatory_obligations IS 'Definition of regulatory reporting obligations';

-- Report templates
CREATE TABLE IF NOT EXISTS regulatory.report_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_code VARCHAR(50) NOT NULL UNIQUE,
    template_name VARCHAR(200) NOT NULL,
    report_type VARCHAR(20) NOT NULL,
    jurisdiction_code VARCHAR(10) NOT NULL,
    format VARCHAR(10) NOT NULL,
    version VARCHAR(20) NOT NULL,
    taxonomy_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    FOREIGN KEY (jurisdiction_code) REFERENCES regulatory.jurisdiction_configs(jurisdiction_code)
);

COMMENT ON TABLE regulatory.report_templates IS 'Regulatory report templates and their configurations';

-- Compliance reports
CREATE TABLE IF NOT EXISTS regulatory.compliance_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id VARCHAR(100) NOT NULL UNIQUE,
    template_code VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    jurisdiction_code VARCHAR(10) NOT NULL,
    reporting_period_start DATE NOT NULL,
    reporting_period_end DATE NOT NULL,
    generation_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    validation_status VARCHAR(20),
    submission_status VARCHAR(20),
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    checksum VARCHAR(128),
    generated_at TIMESTAMP WITH TIME ZONE,
    generated_by VARCHAR(100),
    submitted_at TIMESTAMP WITH TIME ZONE,
    submitted_by VARCHAR(100),
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_code) REFERENCES regulatory.report_templates(template_code),
    FOREIGN KEY (jurisdiction_code) REFERENCES regulatory.jurisdiction_configs(jurisdiction_code)
);

COMMENT ON TABLE regulatory.compliance_reports IS 'Generated compliance reports and their metadata';

-- Report generation status tracking
CREATE TABLE IF NOT EXISTS regulatory.report_generation_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    message TEXT,
    progress_percentage INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES regulatory.compliance_reports(report_id)
);

COMMENT ON TABLE regulatory.report_generation_status IS 'Detailed status tracking for report generation processes';

-- Data validation rules
CREATE TABLE IF NOT EXISTS regulatory.validation_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_code VARCHAR(50) NOT NULL UNIQUE,
    rule_name VARCHAR(200) NOT NULL,
    description TEXT,
    rule_type VARCHAR(20) NOT NULL,
    expression TEXT NOT NULL,
    severity VARCHAR(10) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    jurisdiction_code VARCHAR(10),
    report_type VARCHAR(20),
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    FOREIGN KEY (jurisdiction_code) REFERENCES regulatory.jurisdiction_configs(jurisdiction_code)
);

COMMENT ON TABLE regulatory.validation_rules IS 'Business rules for data validation and compliance checking';

-- Audit log for all regulatory activities
CREATE TABLE IF NOT EXISTS regulatory.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    event_description TEXT NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    old_values JSONB,
    new_values JSONB,
    metadata JSONB,
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100),
    jurisdiction_code VARCHAR(10),
    FOREIGN KEY (jurisdiction_code) REFERENCES regulatory.jurisdiction_configs(jurisdiction_code)
);

COMMENT ON TABLE regulatory.audit_log IS 'Comprehensive audit trail for all regulatory compliance activities';

-- Institutions registry
CREATE TABLE IF NOT EXISTS regulatory.institutions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_code VARCHAR(20) NOT NULL UNIQUE,
    institution_name VARCHAR(200) NOT NULL,
    lei_code VARCHAR(20) UNIQUE,
    tax_id VARCHAR(20),
    country_code VARCHAR(2) NOT NULL,
    jurisdiction_code VARCHAR(10) NOT NULL,
    institution_type VARCHAR(20) NOT NULL,
    regulatory_category VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    registration_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    FOREIGN KEY (jurisdiction_code) REFERENCES regulatory.jurisdiction_configs(jurisdiction_code)
);

COMMENT ON TABLE regulatory.institutions IS 'Registry of financial institutions and their regulatory information';

-- Regulatory deadlines calendar
CREATE TABLE IF NOT EXISTS regulatory.regulatory_calendar (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    obligation_code VARCHAR(50) NOT NULL,
    jurisdiction_code VARCHAR(10) NOT NULL,
    reporting_period_start DATE NOT NULL,
    reporting_period_end DATE NOT NULL,
    deadline_date DATE NOT NULL,
    grace_period_end DATE,
    is_business_day BOOLEAN NOT NULL DEFAULT TRUE,
    holiday_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (obligation_code) REFERENCES regulatory.regulatory_obligations(obligation_code),
    FOREIGN KEY (jurisdiction_code) REFERENCES regulatory.jurisdiction_configs(jurisdiction_code),
    UNIQUE(obligation_code, reporting_period_start, reporting_period_end)
);

COMMENT ON TABLE regulatory.regulatory_calendar IS 'Calendar of regulatory deadlines and reporting periods';

-- Submission tracking
CREATE TABLE IF NOT EXISTS regulatory.submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id VARCHAR(100) NOT NULL UNIQUE,
    report_id VARCHAR(100) NOT NULL,
    submission_method VARCHAR(20) NOT NULL,
    destination VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    submitted_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    confirmation_reference VARCHAR(100),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    FOREIGN KEY (report_id) REFERENCES regulatory.compliance_reports(report_id)
);

COMMENT ON TABLE regulatory.submissions IS 'Tracking of report submissions to regulatory authorities';

-- Data quality metrics
CREATE TABLE IF NOT EXISTS regulatory.data_quality_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_date DATE NOT NULL,
    data_source VARCHAR(100) NOT NULL,
    jurisdiction_code VARCHAR(10),
    total_records BIGINT NOT NULL DEFAULT 0,
    valid_records BIGINT NOT NULL DEFAULT 0,
    invalid_records BIGINT NOT NULL DEFAULT 0,
    completeness_score DECIMAL(5,2),
    accuracy_score DECIMAL(5,2),
    timeliness_score DECIMAL(5,2),
    overall_score DECIMAL(5,2),
    issues JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (jurisdiction_code) REFERENCES regulatory.jurisdiction_configs(jurisdiction_code),
    UNIQUE(metric_date, data_source, jurisdiction_code)
);

COMMENT ON TABLE regulatory.data_quality_metrics IS 'Daily data quality metrics for regulatory data sources';

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_jurisdiction_configs_code ON regulatory.jurisdiction_configs(jurisdiction_code);
CREATE INDEX IF NOT EXISTS idx_jurisdiction_configs_active ON regulatory.jurisdiction_configs(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_customer_jurisdictions_customer ON regulatory.customer_jurisdictions(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_jurisdictions_jurisdiction ON regulatory.customer_jurisdictions(jurisdiction_code);
CREATE INDEX IF NOT EXISTS idx_regulatory_obligations_jurisdiction ON regulatory.regulatory_obligations(jurisdiction_code);
CREATE INDEX IF NOT EXISTS idx_regulatory_obligations_report_type ON regulatory.regulatory_obligations(report_type);
CREATE INDEX IF NOT EXISTS idx_report_templates_jurisdiction ON regulatory.report_templates(jurisdiction_code);
CREATE INDEX IF NOT EXISTS idx_report_templates_active ON regulatory.report_templates(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_compliance_reports_customer ON regulatory.compliance_reports(customer_id);
CREATE INDEX IF NOT EXISTS idx_compliance_reports_status ON regulatory.compliance_reports(generation_status);
CREATE INDEX IF NOT EXISTS idx_compliance_reports_period ON regulatory.compliance_reports(reporting_period_start, reporting_period_end);
CREATE INDEX IF NOT EXISTS idx_validation_rules_type ON regulatory.validation_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_validation_rules_enabled ON regulatory.validation_rules(enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON regulatory.audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON regulatory.audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON regulatory.audit_log(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_institutions_country ON regulatory.institutions(country_code);
CREATE INDEX IF NOT EXISTS idx_institutions_jurisdiction ON regulatory.institutions(jurisdiction_code);
CREATE INDEX IF NOT EXISTS idx_regulatory_calendar_deadline ON regulatory.regulatory_calendar(deadline_date);
CREATE INDEX IF NOT EXISTS idx_regulatory_calendar_obligation ON regulatory.regulatory_calendar(obligation_code);
CREATE INDEX IF NOT EXISTS idx_submissions_report ON regulatory.submissions(report_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON regulatory.submissions(status);
CREATE INDEX IF NOT EXISTS idx_data_quality_metrics_date ON regulatory.data_quality_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_data_quality_metrics_source ON regulatory.data_quality_metrics(data_source);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION regulatory.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_jurisdiction_configs_updated_at
    BEFORE UPDATE ON regulatory.jurisdiction_configs
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_customer_jurisdictions_updated_at
    BEFORE UPDATE ON regulatory.customer_jurisdictions
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_regulatory_obligations_updated_at
    BEFORE UPDATE ON regulatory.regulatory_obligations
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_report_templates_updated_at
    BEFORE UPDATE ON regulatory.report_templates
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_compliance_reports_updated_at
    BEFORE UPDATE ON regulatory.compliance_reports
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_validation_rules_updated_at
    BEFORE UPDATE ON regulatory.validation_rules
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_institutions_updated_at
    BEFORE UPDATE ON regulatory.institutions
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_submissions_updated_at
    BEFORE UPDATE ON regulatory.submissions
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

-- Insert initial migration record
INSERT INTO regulatory.migrations (version, description, applied_by, checksum, success)
VALUES ('001', 'Initial schema creation for ComplianceAI regulatory compliance system', 'system', 'a1b2c3d4e5f678901234567890123456789012345678901234567890123456789012', TRUE);

-- Grant permissions (adjust as needed for your security model)
-- Note: These are example permissions - adjust based on your security requirements

-- Create roles
CREATE ROLE complianceai_readonly;
CREATE ROLE complianceai_readwrite;
CREATE ROLE complianceai_admin;

-- Grant schema usage
GRANT USAGE ON SCHEMA regulatory TO complianceai_readonly, complianceai_readwrite, complianceai_admin;

-- Grant table permissions
GRANT SELECT ON ALL TABLES IN SCHEMA regulatory TO complianceai_readonly;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA regulatory TO complianceai_readwrite;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA regulatory TO complianceai_admin;

-- Grant sequence permissions
GRANT USAGE ON ALL SEQUENCES IN SCHEMA regulatory TO complianceai_readwrite, complianceai_admin;

-- Create views for common queries (optional but recommended for performance)
CREATE OR REPLACE VIEW regulatory.active_jurisdictions AS
SELECT * FROM regulatory.jurisdiction_configs
WHERE is_active = TRUE AND (effective_to IS NULL OR effective_to > CURRENT_DATE);

CREATE OR REPLACE VIEW regulatory.upcoming_deadlines AS
SELECT
    rc.*,
    ro.obligation_name,
    ro.frequency,
    jc.jurisdiction_name
FROM regulatory.regulatory_calendar rc
JOIN regulatory.regulatory_obligations ro ON rc.obligation_code = ro.obligation_code
JOIN regulatory.jurisdiction_configs jc ON rc.jurisdiction_code = jc.jurisdiction_code
WHERE rc.deadline_date >= CURRENT_DATE
  AND rc.deadline_date <= CURRENT_DATE + INTERVAL '30 days'
ORDER BY rc.deadline_date;

-- Comments for views
COMMENT ON VIEW regulatory.active_jurisdictions IS 'View of currently active jurisdictions';
COMMENT ON VIEW regulatory.upcoming_deadlines IS 'View of upcoming regulatory deadlines within 30 days';
