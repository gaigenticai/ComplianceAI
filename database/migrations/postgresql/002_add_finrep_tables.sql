-- ComplianceAI PostgreSQL Database Migration
-- Version: 002
-- Description: Add FINREP-specific tables and indexes
-- Date: 2024-01-15
-- Author: ComplianceAI Development Team

-- Start transaction for atomic migration
BEGIN;

-- Insert migration record
INSERT INTO regulatory.migrations (version, description, applied_by, success)
VALUES ('002', 'Add FINREP-specific tables and indexes', 'system', FALSE);

-- FINREP Balance Sheet data table
CREATE TABLE IF NOT EXISTS regulatory.finrep_balance_sheet (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id VARCHAR(20) NOT NULL,
    reporting_date DATE NOT NULL,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'EUR',
    consolidation_level VARCHAR(20) NOT NULL DEFAULT 'solo',

    -- Assets
    cash_and_balances_with_central_banks DECIMAL(20,2),
    financial_assets_held_for_trading DECIMAL(20,2),
    derivative_financial_instruments DECIMAL(20,2),
    equity_instruments DECIMAL(20,2),
    debt_securities DECIMAL(20,2),
    loans_and_advances_to_banks DECIMAL(20,2),
    loans_and_advances_to_customers DECIMAL(20,2),
    investment_property DECIMAL(20,2),
    property_plant_equipment DECIMAL(20,2),
    intangible_assets DECIMAL(20,2),
    other_assets DECIMAL(20,2),
    total_assets DECIMAL(20,2),

    -- Liabilities
    deposits_from_banks DECIMAL(20,2),
    deposits_from_customers DECIMAL(20,2),
    debt_securities_issued DECIMAL(20,2),
    financial_liabilities_held_for_trading DECIMAL(20,2),
    derivative_financial_liabilities DECIMAL(20,2),
    other_liabilities DECIMAL(20,2),
    provisions DECIMAL(20,2),
    total_liabilities DECIMAL(20,2),

    -- Equity
    share_capital DECIMAL(20,2),
    retained_earnings DECIMAL(20,2),
    other_reserves DECIMAL(20,2),
    total_equity DECIMAL(20,2),

    -- Metadata
    data_source VARCHAR(100),
    quality_score DECIMAL(5,2),
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),

    -- Constraints
    CONSTRAINT finrep_bs_balance_check CHECK (total_assets = total_liabilities + total_equity),
    CONSTRAINT finrep_bs_positive_assets CHECK (total_assets > 0),
    CONSTRAINT finrep_bs_positive_equity CHECK (total_equity > 0),
    FOREIGN KEY (institution_id) REFERENCES regulatory.institutions(institution_code),
    UNIQUE(institution_id, reporting_date, consolidation_level)
);

COMMENT ON TABLE regulatory.finrep_balance_sheet IS 'FINREP Balance Sheet data with detailed asset, liability, and equity breakdowns';

-- FINREP Income Statement data table
CREATE TABLE IF NOT EXISTS regulatory.finrep_income_statement (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id VARCHAR(20) NOT NULL,
    reporting_date DATE NOT NULL,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'EUR',
    consolidation_level VARCHAR(20) NOT NULL DEFAULT 'solo',
    period_type VARCHAR(10) NOT NULL DEFAULT 'annual', -- annual, quarterly

    -- Interest income
    interest_income_on_financial_assets DECIMAL(20,2),
    interest_expense_on_financial_liabilities DECIMAL(20,2),
    net_interest_income DECIMAL(20,2),

    -- Fee and commission income
    fee_and_commission_income DECIMAL(20,2),
    fee_and_commission_expense DECIMAL(20,2),
    net_fee_and_commission_income DECIMAL(20,2),

    -- Trading income
    net_trading_income DECIMAL(20,2),

    -- Other income
    other_operating_income DECIMAL(20,2),
    total_operating_income DECIMAL(20,2),

    -- Operating expenses
    staff_expenses DECIMAL(20,2),
    administrative_expenses DECIMAL(20,2),
    depreciation_amortization DECIMAL(20,2),
    other_operating_expenses DECIMAL(20,2),
    total_operating_expenses DECIMAL(20,2),

    -- Profit/Loss
    operating_profit_loss DECIMAL(20,2),
    impairment_losses DECIMAL(20,2),
    profit_loss_before_tax DECIMAL(20,2),
    tax_expense DECIMAL(20,2),
    profit_loss DECIMAL(20,2),

    -- Metadata
    data_source VARCHAR(100),
    quality_score DECIMAL(5,2),
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),

    -- Constraints
    FOREIGN KEY (institution_id) REFERENCES regulatory.institutions(institution_code),
    UNIQUE(institution_id, reporting_date, consolidation_level, period_type)
);

COMMENT ON TABLE regulatory.finrep_income_statement IS 'FINREP Income Statement data with detailed revenue and expense breakdowns';

-- FINREP geographical data table
CREATE TABLE IF NOT EXISTS regulatory.finrep_geographical_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id VARCHAR(20) NOT NULL,
    reporting_date DATE NOT NULL,
    consolidation_level VARCHAR(20) NOT NULL DEFAULT 'solo',

    -- Geographical breakdown
    country_code VARCHAR(2) NOT NULL,
    region VARCHAR(50),
    loans_and_advances DECIMAL(20,2),
    deposits DECIMAL(20,2),
    net_interest_income DECIMAL(20,2),
    risk_weighted_assets DECIMAL(20,2),

    -- Metadata
    data_source VARCHAR(100),
    quality_score DECIMAL(5,2),
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),

    -- Constraints
    FOREIGN KEY (institution_id) REFERENCES regulatory.institutions(institution_code),
    UNIQUE(institution_id, reporting_date, consolidation_level, country_code)
);

COMMENT ON TABLE regulatory.finrep_geographical_data IS 'FINREP geographical breakdown of assets, liabilities, and income by country/region';

-- FINREP forbearance data table
CREATE TABLE IF NOT EXISTS regulatory.finrep_forbearance_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id VARCHAR(20) NOT NULL,
    reporting_date DATE NOT NULL,
    consolidation_level VARCHAR(20) NOT NULL DEFAULT 'solo',

    -- Forbearance measures
    forborne_exposures_gross DECIMAL(20,2),
    forborne_exposures_net DECIMAL(20,2),
    forbearance_measures_count INTEGER,
    modified_terms_count INTEGER,
    payment_holidays_count INTEGER,
    principal_deferrals DECIMAL(20,2),
    interest_rate_reductions DECIMAL(20,2),

    -- Metadata
    data_source VARCHAR(100),
    quality_score DECIMAL(5,2),
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),

    -- Constraints
    FOREIGN KEY (institution_id) REFERENCES regulatory.institutions(institution_code),
    UNIQUE(institution_id, reporting_date, consolidation_level)
);

COMMENT ON TABLE regulatory.finrep_forbearance_data IS 'FINREP forbearance measures and modified terms data';

-- COREP data tables
CREATE TABLE IF NOT EXISTS regulatory.corep_own_funds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id VARCHAR(20) NOT NULL,
    reporting_date DATE NOT NULL,
    consolidation_level VARCHAR(20) NOT NULL DEFAULT 'solo',

    -- Common Equity Tier 1 (CET1)
    cet1_common_shares DECIMAL(20,2),
    cet1_retained_earnings DECIMAL(20,2),
    cet1_other_reserves DECIMAL(20,2),
    cet1_minority_interests DECIMAL(20,2),
    cet1_total DECIMAL(20,2),

    -- Additional Tier 1 (AT1)
    at1_instruments DECIMAL(20,2),
    at1_total DECIMAL(20,2),

    -- Tier 2 (T2)
    t2_instruments DECIMAL(20,2),
    t2_total DECIMAL(20,2),

    -- Total Capital
    total_capital DECIMAL(20,2),
    total_risk_weighted_assets DECIMAL(20,2),
    cet1_ratio DECIMAL(5,2),
    total_capital_ratio DECIMAL(5,2),

    -- Metadata
    data_source VARCHAR(100),
    quality_score DECIMAL(5,2),
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),

    -- Constraints
    FOREIGN KEY (institution_id) REFERENCES regulatory.institutions(institution_code),
    UNIQUE(institution_id, reporting_date, consolidation_level)
);

COMMENT ON TABLE regulatory.corep_own_funds IS 'COREP Own Funds and capital adequacy data';

-- Create indexes for FINREP tables
CREATE INDEX IF NOT EXISTS idx_finrep_bs_institution_date ON regulatory.finrep_balance_sheet(institution_id, reporting_date);
CREATE INDEX IF NOT EXISTS idx_finrep_bs_validation_status ON regulatory.finrep_balance_sheet(validation_status);
CREATE INDEX IF NOT EXISTS idx_finrep_is_institution_date ON regulatory.finrep_income_statement(institution_id, reporting_date);
CREATE INDEX IF NOT EXISTS idx_finrep_is_validation_status ON regulatory.finrep_income_statement(validation_status);
CREATE INDEX IF NOT EXISTS idx_finrep_geo_institution_date ON regulatory.finrep_geographical_data(institution_id, reporting_date);
CREATE INDEX IF NOT EXISTS idx_finrep_geo_country ON regulatory.finrep_geographical_data(country_code);
CREATE INDEX IF NOT EXISTS idx_finrep_forb_institution_date ON regulatory.finrep_forbearance_data(institution_id, reporting_date);
CREATE INDEX IF NOT EXISTS idx_corep_of_institution_date ON regulatory.corep_own_funds(institution_id, reporting_date);

-- Create triggers for updated_at
CREATE TRIGGER update_finrep_bs_updated_at
    BEFORE UPDATE ON regulatory.finrep_balance_sheet
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_finrep_is_updated_at
    BEFORE UPDATE ON regulatory.finrep_income_statement
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_finrep_geo_updated_at
    BEFORE UPDATE ON regulatory.finrep_geographical_data
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_finrep_forb_updated_at
    BEFORE UPDATE ON regulatory.finrep_forbearance_data
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

CREATE TRIGGER update_corep_of_updated_at
    BEFORE UPDATE ON regulatory.corep_own_funds
    FOR EACH ROW EXECUTE FUNCTION regulatory.update_updated_at_column();

-- Insert sample data for testing (optional - remove in production)
-- INSERT INTO regulatory.finrep_balance_sheet (
--     institution_id, reporting_date, total_assets, total_liabilities, total_equity
-- ) VALUES (
--     'TEST001', '2023-12-31', 1000000000.00, 900000000.00, 100000000.00
-- );

-- Update migration status
UPDATE regulatory.migrations
SET success = TRUE, checksum = 'finrep-tables-checksum'
WHERE version = '002';

-- Grant permissions on new tables
GRANT SELECT ON regulatory.finrep_balance_sheet TO complianceai_readonly;
GRANT SELECT ON regulatory.finrep_income_statement TO complianceai_readonly;
GRANT SELECT ON regulatory.finrep_geographical_data TO complianceai_readonly;
GRANT SELECT ON regulatory.finrep_forbearance_data TO complianceai_readonly;
GRANT SELECT ON regulatory.corep_own_funds TO complianceai_readonly;

GRANT SELECT, INSERT, UPDATE ON regulatory.finrep_balance_sheet TO complianceai_readwrite;
GRANT SELECT, INSERT, UPDATE ON regulatory.finrep_income_statement TO complianceai_readwrite;
GRANT SELECT, INSERT, UPDATE ON regulatory.finrep_geographical_data TO complianceai_readwrite;
GRANT SELECT, INSERT, UPDATE ON regulatory.finrep_forbearance_data TO complianceai_readwrite;
GRANT SELECT, INSERT, UPDATE ON regulatory.corep_own_funds TO complianceai_readwrite;

GRANT ALL PRIVILEGES ON regulatory.finrep_balance_sheet TO complianceai_admin;
GRANT ALL PRIVILEGES ON regulatory.finrep_income_statement TO complianceai_admin;
GRANT ALL PRIVILEGES ON regulatory.finrep_geographical_data TO complianceai_admin;
GRANT ALL PRIVILEGES ON regulatory.finrep_forbearance_data TO complianceai_admin;
GRANT ALL PRIVILEGES ON regulatory.corep_own_funds TO complianceai_admin;

-- Create views for FINREP reporting
CREATE OR REPLACE VIEW regulatory.finrep_balance_sheet_summary AS
SELECT
    institution_id,
    reporting_date,
    currency_code,
    consolidation_level,
    total_assets,
    total_liabilities,
    total_equity,
    total_assets - (total_liabilities + total_equity) as balance_difference,
    CASE
        WHEN total_assets = total_liabilities + total_equity THEN 'BALANCED'
        ELSE 'UNBALANCED'
    END as balance_status,
    quality_score,
    validation_status,
    created_at
FROM regulatory.finrep_balance_sheet
ORDER BY reporting_date DESC, institution_id;

COMMENT ON VIEW regulatory.finrep_balance_sheet_summary IS 'Summary view of FINREP balance sheet data with balance validation';

-- Commit transaction
COMMIT;
