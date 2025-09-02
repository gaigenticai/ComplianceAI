# Database Migrations

This directory contains database migration scripts for ComplianceAI, supporting both PostgreSQL and MongoDB databases.

## Directory Structure

```
migrations/
├── postgresql/           # PostgreSQL migration scripts
│   ├── 001_initial_schema.sql
│   └── 002_add_finrep_tables.sql
├── mongodb/             # MongoDB migration scripts
│   └── 001_initial_collections.js
└── scripts/             # Migration management scripts
    └── migration_manager.py
```

## Migration Files

### PostgreSQL Migrations

#### 001_initial_schema.sql
- **Purpose**: Creates the initial database schema for regulatory compliance
- **Tables Created**:
  - `regulatory.migrations` - Migration tracking
  - `regulatory.jurisdiction_configs` - Jurisdiction configurations
  - `regulatory.customer_jurisdictions` - Customer-jurisdiction mappings
  - `regulatory.regulatory_obligations` - Regulatory requirements
  - `regulatory.report_templates` - Report templates
  - `regulatory.compliance_reports` - Generated reports
  - `regulatory.validation_rules` - Business rules
  - `regulatory.audit_log` - Audit trail
  - `regulatory.institutions` - Financial institutions registry
  - `regulatory.regulatory_calendar` - Deadline calendar
  - `regulatory.submissions` - Report submissions
  - `regulatory.data_quality_metrics` - Data quality tracking

#### 002_add_finrep_tables.sql
- **Purpose**: Adds FINREP-specific tables for detailed financial reporting
- **Tables Created**:
  - `regulatory.finrep_balance_sheet` - Balance sheet data
  - `regulatory.finrep_income_statement` - Income statement data
  - `regulatory.finrep_geographical_data` - Geographical breakdowns
  - `regulatory.finrep_forbearance_data` - Forbearance measures
  - `regulatory.corep_own_funds` - COREP capital data

### MongoDB Migrations

#### 001_initial_collections.js
- **Purpose**: Creates initial MongoDB collections with schema validation
- **Collections Created**:
  - `regulatory_documents` - Regulatory document storage
  - `regulatory_requirements` - Parsed regulatory requirements
  - `compliance_rules` - JSON-Logic rule definitions
  - `document_parsing_results` - Document parsing results
  - `audit_events` - Audit trail events
  - `report_templates` - Report template definitions
  - `workflow_definitions` - Workflow configurations
  - `system_metrics` - System performance metrics (capped)
  - `performance_logs` - Performance logs (capped)

## Using the Migration Manager

The `migration_manager.py` script provides comprehensive migration management capabilities.

### Prerequisites

Install required Python packages:
```bash
pip install psycopg2-binary pymongo
```

### Environment Variables

Set the following environment variables:

```bash
# PostgreSQL Configuration
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=complianceai
export DB_USER=complianceai
export DB_PASSWORD=your_password
export DB_SSL_MODE=require

# MongoDB Configuration
export MONGODB_URL=mongodb://localhost:27017/complianceai
export MONGODB_DB=complianceai

# Migration Configuration
export MIGRATION_PATH=/path/to/migrations
```

### Commands

#### Check Migration Status
```bash
# Check all databases
python migration_manager.py status

# Check specific database
python migration_manager.py status --db-type postgresql
python migration_manager.py status --db-type mongodb
```

#### Apply Migrations
```bash
# Apply all pending migrations
python migration_manager.py apply

# Apply to specific database
python migration_manager.py apply --db-type postgresql

# Apply up to specific version
python migration_manager.py apply --target 001

# Dry run (show what would be done)
python migration_manager.py apply --dry-run

# Force apply without confirmation
python migration_manager.py apply --force
```

#### Validate Migrations
```bash
# Validate all migrations
python migration_manager.py validate

# Validate specific database
python migration_manager.py validate --db-type postgresql
```

#### Generate Reports
```bash
# Generate migration report
python migration_manager.py report

# Generate report for specific database
python migration_manager.py report --db-type mongodb
```

#### Verbose Output
```bash
# Enable verbose logging for all commands
python migration_manager.py status --verbose
```

## Manual Migration Application

If you prefer to apply migrations manually:

### PostgreSQL

```bash
# Connect to PostgreSQL
psql -h localhost -U complianceai -d complianceai

# Apply migration
\i migrations/postgresql/001_initial_schema.sql
\i migrations/postgresql/002_add_finrep_tables.sql
```

### MongoDB

```bash
# Apply MongoDB migration
mongosh complianceai < migrations/mongodb/001_initial_collections.js
```

## Migration Best Practices

### Development Workflow

1. **Create Migration Files**:
   ```bash
   # PostgreSQL migration
   touch migrations/postgresql/003_add_new_feature.sql

   # MongoDB migration
   touch migrations/mongodb/002_add_new_collection.js
   ```

2. **Write Migration Content**:
   - Use descriptive names for migration files
   - Include comments explaining the purpose
   - Add rollback instructions where possible
   - Test migrations in development environment

3. **Test Migrations**:
   ```bash
   # Test in development
   python migration_manager.py apply --dry-run --verbose

   # Apply to development database
   python migration_manager.py apply --db-type postgresql
   ```

4. **Version Control**:
   - Commit migration files with application code
   - Tag releases with migration versions
   - Document breaking changes

### Production Deployment

1. **Backup Database**:
   ```bash
   # PostgreSQL backup
   pg_dump -h localhost -U complianceai complianceai > backup_$(date +%Y%m%d).sql

   # MongoDB backup
   mongodump --db complianceai --out backup_$(date +%Y%m%d)
   ```

2. **Apply Migrations**:
   ```bash
   # Apply in staging first
   python migration_manager.py apply --db-type all

   # Verify application still works
   # Then apply to production
   ```

3. **Monitor Application**:
   - Check application logs for errors
   - Monitor database performance
   - Validate data integrity

### Rollback Procedures

**Important**: Always test rollback procedures in development before production use.

#### PostgreSQL Rollback
```sql
-- Example rollback (customize based on migration)
DROP TABLE IF EXISTS regulatory.new_table;
DELETE FROM regulatory.migrations WHERE version = '003';
```

#### MongoDB Rollback
```javascript
// Example rollback (customize based on migration)
db.new_collection.drop();
db.migrations.deleteOne({version: "002"});
```

## Migration File Naming Convention

Migration files follow this naming convention:
- `{version}_{description}.{extension}`
- Version: 3-digit number with leading zeros (001, 002, etc.)
- Description: snake_case description of changes
- Extension: `.sql` for PostgreSQL, `.js` for MongoDB

Examples:
- `001_initial_schema.sql`
- `002_add_finrep_tables.sql`
- `001_initial_collections.js`
- `002_add_validation_rules.js`

## Schema Validation

### PostgreSQL Constraints

All tables include:
- Primary key constraints
- Foreign key constraints
- Check constraints for data validation
- Unique constraints where appropriate
- Not null constraints for required fields

### MongoDB Schema Validation

Collections use JSON Schema validation:
```javascript
validator: {
  $jsonSchema: {
    bsonType: "object",
    required: ["field1", "field2"],
    properties: {
      field1: { bsonType: "string" },
      field2: { bsonType: "date" }
    }
  }
}
```

## Performance Considerations

### Indexes

All migrations create appropriate indexes:
- Primary key indexes (automatic)
- Foreign key indexes
- Query-specific indexes
- Partial indexes for active records

### Partitioning

Consider table partitioning for large tables:
```sql
-- Example partitioning by date
CREATE TABLE regulatory.audit_log_y2024 PARTITION OF regulatory.audit_log
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### Archiving

Implement data archiving for old records:
```sql
-- Archive old audit logs
CREATE TABLE regulatory.audit_log_archive AS
SELECT * FROM regulatory.audit_log
WHERE event_timestamp < CURRENT_DATE - INTERVAL '7 years';
```

## Monitoring and Alerting

### Migration Metrics

Monitor migration performance:
```sql
-- Query migration execution time
SELECT version, applied_at,
       EXTRACT(EPOCH FROM (applied_at - LAG(applied_at) OVER (ORDER BY version))) as duration_seconds
FROM regulatory.migrations
ORDER BY version;
```

### Database Health Checks

Regular health checks:
```sql
-- Check table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'regulatory'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_indexes
JOIN pg_class ON pg_class.relname = pg_indexes.indexname
WHERE schemaname = 'regulatory'
ORDER BY pg_relation_size(indexrelid) DESC;
```

## Troubleshooting

### Common Issues

#### Migration Fails to Apply

1. **Check Database Connection**:
   ```bash
   # Test PostgreSQL connection
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1"

   # Test MongoDB connection
   mongosh $MONGODB_URL --eval "db.runCommand({ping: 1})"
   ```

2. **Check File Permissions**:
   ```bash
   ls -la migrations/postgresql/
   ls -la migrations/mongodb/
   ```

3. **Review Error Logs**:
   ```bash
   python migration_manager.py apply --verbose
   ```

#### Migration Checksum Mismatch

1. **Validate Migration Files**:
   ```bash
   python migration_manager.py validate
   ```

2. **Check File Encoding**:
   ```bash
   file migrations/postgresql/001_initial_schema.sql
   ```

3. **Verify File Integrity**:
   ```bash
   sha256sum migrations/postgresql/001_initial_schema.sql
   ```

#### Database Lock Conflicts

1. **Check Active Connections**:
   ```sql
   SELECT * FROM pg_stat_activity WHERE state != 'idle';
   ```

2. **Kill Long-Running Queries**:
   ```sql
   SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';
   ```

## Security Considerations

### Database Credentials

- Store credentials securely (not in code)
- Use different credentials for different environments
- Rotate credentials regularly
- Use SSL/TLS for database connections

### Access Control

```sql
-- Create read-only user
CREATE USER complianceai_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE complianceai TO complianceai_readonly;
GRANT USAGE ON SCHEMA regulatory TO complianceai_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA regulatory TO complianceai_readonly;

-- Create read-write user
CREATE USER complianceai_readwrite WITH PASSWORD 'readwrite_password';
GRANT CONNECT ON DATABASE complianceai TO complianceai_readwrite;
GRANT USAGE ON SCHEMA regulatory TO complianceai_readwrite;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA regulatory TO complianceai_readwrite;
```

### Audit Logging

All migrations include audit logging setup:
- Track all data changes
- Log user actions
- Maintain immutable audit trail
- Regular audit log rotation

## Support and Maintenance

### Regular Maintenance Tasks

**Daily**:
- Monitor migration status
- Review failed migrations
- Check database performance

**Weekly**:
- Validate migration integrity
- Review database growth
- Update migration documentation

**Monthly**:
- Archive old migration files
- Review access permissions
- Update backup procedures

### Documentation Updates

Keep migration documentation current:
- Update README with new migration files
- Document breaking changes
- Maintain change log
- Update troubleshooting guides

### Getting Help

- **Migration Issues**: Check the troubleshooting section above
- **Database Issues**: Refer to PostgreSQL/MongoDB documentation
- **Application Issues**: Contact the ComplianceAI development team
- **Security Issues**: Contact the security team immediately

## Version History

- **v1.0**: Initial migration system with PostgreSQL and MongoDB support
- **v1.1**: Added FINREP tables and MongoDB collections
- **v1.2**: Enhanced migration manager with rollback support
- **v1.3**: Added performance monitoring and validation checks
