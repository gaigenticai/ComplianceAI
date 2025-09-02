# Data Migration Tools

This directory contains comprehensive data migration and validation tools for the ComplianceAI system. These tools support migrating data between different environments, validating data integrity, and ensuring compliance with regulatory requirements.

## Directory Structure

```
data_migration/
├── postgresql/              # PostgreSQL migration tools
│   └── data_migration_tool.py
├── mongodb/                 # MongoDB migration tools
│   └── mongo_migration_tool.py
├── kafka/                   # Kafka data migration tools
│   └── kafka_migration_tool.py
└── validation/              # Data validation tools
    └── data_validator.py
```

## PostgreSQL Data Migration Tool

### Features

- **Full/Partial Migration**: Migrate all tables or specific tables only
- **Parallel Processing**: Multi-threaded migration for better performance
- **Data Validation**: Built-in validation during migration
- **Backup/Restore**: Create backups and restore from backups
- **Progress Tracking**: Real-time progress monitoring
- **Error Handling**: Comprehensive error handling and recovery

### Usage Examples

#### Migrate Data Between Environments

```bash
# Migrate all tables from dev to staging
python postgresql/data_migration_tool.py migrate \
  --source-db "postgresql://user:pass@dev-db/complianceai" \
  --target-db "postgresql://user:pass@staging-db/complianceai" \
  --workers 8 \
  --batch-size 5000

# Migrate specific tables only
python postgresql/data_migration_tool.py migrate \
  --tables regulatory.jurisdiction_configs,regulatory.regulatory_obligations \
  --source-db "postgresql://user:pass@source-db/db" \
  --target-db "postgresql://user:pass@target-db/db"
```

#### Create Database Backup

```bash
# Create compressed backup of all tables
python postgresql/data_migration_tool.py backup \
  --source-db "postgresql://user:pass@source-db/db" \
  --backup-file ./backups/complianceai_backup_20240115.sql.gz

# Backup specific tables
python postgresql/data_migration_tool.py backup \
  --tables regulatory.finrep_balance_sheet,regulatory.corep_own_funds \
  --source-db "postgresql://user:pass@source-db/db" \
  --backup-file ./backups/finrep_backup.sql.gz
```

#### Validate Migration

```bash
# Validate data integrity after migration
python postgresql/data_migration_tool.py validate \
  --source-db "postgresql://user:pass@source-db/db" \
  --target-db "postgresql://user:pass@target-db/db"

# Generate detailed validation report
python postgresql/data_migration_tool.py validate \
  --report-file ./reports/migration_validation_20240115.json \
  --source-db "postgresql://user:pass@source-db/db" \
  --target-db "postgresql://user:pass@target-db/db"
```

#### Analyze Database

```bash
# Get database statistics and analysis
python postgresql/data_migration_tool.py analyze \
  --source-db "postgresql://user:pass@source-db/db"
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--source-db` | Source database connection string | - |
| `--target-db` | Target database connection string | - |
| `--tables` | Comma-separated list of tables | All tables |
| `--batch-size` | Records per batch | 1000 |
| `--workers` | Number of parallel workers | 4 |
| `--backup-file` | Backup file path | Auto-generated |
| `--report-file` | Migration report file path | - |
| `--dry-run` | Show what would be done | False |
| `--force` | Force operation | False |
| `--verbose` | Enable verbose output | False |

## MongoDB Data Migration Tool

### Features

- **Collection Migration**: Migrate MongoDB collections between databases
- **Document Validation**: Validate document structure during migration
- **Index Preservation**: Maintain database indexes in target
- **Progress Monitoring**: Real-time migration progress
- **Error Recovery**: Automatic retry and error handling

### Usage Examples

#### Migrate Collections

```bash
# Migrate all collections from dev to staging
python mongodb/mongo_migration_tool.py migrate \
  --source-uri "mongodb://user:pass@dev-mongo/complianceai" \
  --target-uri "mongodb://user:pass@staging-mongo/complianceai" \
  --database complianceai \
  --workers 6 \
  --batch-size 2000

# Migrate specific collections
python mongodb/mongo_migration_tool.py migrate \
  --collections regulatory_documents,compliance_rules \
  --source-uri "mongodb://source/db" \
  --target-uri "mongodb://target/db" \
  --database complianceai
```

#### Create Backup

```bash
# Create compressed backup of collections
python mongodb/mongo_migration_tool.py backup \
  --source-uri "mongodb://source/db" \
  --database complianceai \
  --backup-file ./backups/mongodb_backup_20240115.json.gz

# Backup specific collections
python mongodb/mongo_migration_tool.py backup \
  --collections audit_events,report_templates \
  --source-uri "mongodb://source/db" \
  --database complianceai \
  --backup-file ./backups/audit_backup.json.gz
```

#### Validate Migration

```bash
# Validate collection migration
python mongodb/mongo_migration_tool.py validate \
  --source-uri "mongodb://source/db" \
  --target-uri "mongodb://target/db" \
  --database complianceai

# Generate validation report
python mongodb/mongo_migration_tool.py validate \
  --report-file ./reports/mongo_validation_20240115.json \
  --source-uri "mongodb://source/db" \
  --target-uri "mongodb://target/db" \
  --database complianceai
```

## Data Validation Tool

### Features

- **Multi-Database Support**: Validate PostgreSQL and MongoDB
- **Comprehensive Checks**: Integrity, consistency, completeness, accuracy
- **Compliance Validation**: Regulatory compliance checks
- **Performance Monitoring**: Database performance validation
- **Automated Reporting**: Generate detailed validation reports

### Validation Checks

#### Integrity Checks
- Referential integrity validation
- Foreign key constraint verification
- Orphaned record detection
- Index consistency checks

#### Consistency Checks
- Cross-table data consistency
- Business rule validation
- Date range validation
- Balance sheet reconciliation

#### Completeness Checks
- Required field validation
- Null value analysis
- Data coverage assessment
- Missing record identification

#### Accuracy Checks
- Data format validation
- Range and limit checks
- Currency code validation
- Date consistency validation

### Usage Examples

#### Run All Validation Checks

```bash
# Validate all data in PostgreSQL
python validation/data_validator.py validate \
  --db-type postgresql \
  --connection "postgresql://user:pass@host/db" \
  --output-dir ./reports

# Validate specific checks only
python validation/data_validator.py validate \
  --checks integrity,consistency,completeness \
  --db-type postgresql \
  --connection "postgresql://user:pass@host/db"
```

#### Generate Validation Report

```bash
# Generate JSON validation report
python validation/data_validator.py report \
  --db-type postgresql \
  --connection "postgresql://user:pass@host/db" \
  --output-dir ./reports \
  --output-format json

# Generate CSV summary report
python validation/data_validator.py report \
  --output-format csv \
  --output-dir ./reports
```

#### Monitor Data Quality

```bash
# Continuous data quality monitoring
python validation/data_validator.py monitor \
  --db-type all \
  --connection "postgresql://user:pass@host/db" \
  --threshold 0.95
```

### Validation Reports

The validation tool generates comprehensive reports including:

- **Summary Statistics**: Overall validation status and scores
- **Detailed Issues**: Specific validation failures and warnings
- **Performance Metrics**: Database performance indicators
- **Recommendations**: Suggested fixes for identified issues
- **Trend Analysis**: Historical validation trends

## Migration Best Practices

### Pre-Migration Preparation

1. **Backup Source Data**:
   ```bash
   # PostgreSQL backup
   python postgresql/data_migration_tool.py backup --source-db "postgresql://..." --backup-file pre_migration_backup.sql.gz

   # MongoDB backup
   python mongodb/mongo_migration_tool.py backup --source-uri "mongodb://..." --backup-file pre_migration_backup.json.gz
   ```

2. **Validate Source Data**:
   ```bash
   # Run comprehensive validation
   python validation/data_validator.py validate --db-type all --connection "..." --checks integrity,consistency,completeness,accuracy
   ```

3. **Plan Migration Window**:
   - Schedule during low-traffic periods
   - Notify stakeholders of maintenance window
   - Prepare rollback procedures

### Migration Execution

1. **Test Migration**:
   ```bash
   # Dry run first
   python postgresql/data_migration_tool.py migrate --dry-run --source-db "..." --target-db "..."

   # Test with small dataset
   python postgresql/data_migration_tool.py migrate --tables test_table --source-db "..." --target-db "..."
   ```

2. **Execute Migration**:
   ```bash
   # Full migration with progress monitoring
   python postgresql/data_migration_tool.py migrate --source-db "..." --target-db "..." --workers 8 --verbose
   ```

3. **Validate Results**:
   ```bash
   # Comprehensive validation
   python validation/data_validator.py validate --source-db "..." --target-db "..." --report-file migration_validation.json
   ```

### Post-Migration Tasks

1. **Update Application Configuration**:
   - Point application to new database
   - Update connection strings
   - Test application functionality

2. **Monitor Performance**:
   ```bash
   # Monitor migrated database performance
   python validation/data_validator.py validate --checks performance --db-type postgresql --connection "..."
   ```

3. **Optimize as Needed**:
   ```bash
   # Rebuild indexes if necessary
   # Update statistics
   # Adjust configuration parameters
   ```

## Environment-Specific Configurations

### Development Environment

```bash
# Small datasets, fast migration
python postgresql/data_migration_tool.py migrate \
  --batch-size 1000 \
  --workers 2 \
  --source-db "postgresql://dev/db" \
  --target-db "postgresql://dev/db"
```

### Staging Environment

```bash
# Medium datasets, balanced performance
python postgresql/data_migration_tool.py migrate \
  --batch-size 5000 \
  --workers 4 \
  --source-db "postgresql://staging/db" \
  --target-db "postgresql://staging/db"
```

### Production Environment

```bash
# Large datasets, maximum performance and safety
python postgresql/data_migration_tool.py migrate \
  --batch-size 10000 \
  --workers 8 \
  --source-db "postgresql://prod/db" \
  --target-db "postgresql://prod/db" \
  --verbose \
  --report-file production_migration_$(date +%Y%m%d_%H%M%S).json
```

## Troubleshooting

### Common Migration Issues

#### Connection Problems

**PostgreSQL Connection Failed**:
```bash
# Check connection string
psql "postgresql://user:pass@host/db" -c "SELECT 1"

# Verify network connectivity
telnet host 5432

# Check authentication
psql -h host -U user -d db
```

**MongoDB Connection Failed**:
```bash
# Test MongoDB connection
mongosh "mongodb://user:pass@host/db" --eval "db.runCommand({ping: 1})"

# Check MongoDB logs
docker logs mongodb_container
```

#### Performance Issues

**Slow Migration**:
- Increase batch size: `--batch-size 10000`
- Add more workers: `--workers 8`
- Check network bandwidth
- Monitor disk I/O

**Memory Issues**:
- Reduce batch size: `--batch-size 1000`
- Decrease worker count: `--workers 2`
- Monitor memory usage during migration

#### Data Integrity Issues

**Validation Failures**:
```bash
# Run detailed validation
python validation/data_validator.py validate --verbose --checks integrity,consistency

# Check specific tables
python postgresql/data_migration_tool.py analyze --source-db "..."
```

**Constraint Violations**:
```sql
-- Check for constraint violations
SELECT * FROM pg_constraint WHERE schemaname = 'regulatory';
```

### Recovery Procedures

#### Rollback Migration

**PostgreSQL Rollback**:
```bash
# Restore from backup
pg_restore -h host -U user -d db pre_migration_backup.sql

# Or drop and recreate target tables
# (Custom rollback procedures needed)
```

**MongoDB Rollback**:
```bash
# Restore from backup
mongorestore --db target_db --drop backup_directory/

# Or drop collections and restore
# (Custom rollback procedures needed)
```

#### Data Repair

**Fix Validation Issues**:
```bash
# Use the fix command (when implemented)
python validation/data_validator.py fix --db-type postgresql --connection "..."
```

## Monitoring and Alerting

### Migration Monitoring

```bash
# Monitor migration progress
watch -n 30 'python postgresql/data_migration_tool.py analyze --source-db "..."'

# Check system resources
top -p $(pgrep -f migration_tool)

# Monitor database connections
psql -h host -U user -d db -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
```

### Automated Alerts

Set up alerts for:
- Migration failures
- Performance degradation
- Data validation errors
- Resource exhaustion

## Security Considerations

### Connection Security

- Use SSL/TLS for all database connections
- Store credentials securely (not in scripts)
- Use read-only connections for source databases
- Implement connection timeouts

### Data Protection

- Encrypt backups at rest and in transit
- Implement access controls on migration tools
- Audit all migration activities
- Comply with data residency requirements

### Access Control

```sql
-- Create migration user with limited privileges
CREATE USER migration_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE complianceai TO migration_user;
GRANT SELECT ON ALL TABLES IN SCHEMA regulatory TO migration_user;
GRANT INSERT, UPDATE ON target_tables TO migration_user;
```

## Performance Optimization

### Database Tuning

**PostgreSQL Optimization**:
```sql
-- Increase maintenance work memory
ALTER SYSTEM SET maintenance_work_mem = '256MB';

-- Adjust checkpoint settings
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';

-- Reload configuration
SELECT pg_reload_conf();
```

**MongoDB Optimization**:
```javascript
// Increase WiredTiger cache
db.adminCommand({setParameter: 1, wiredTigerMaxCacheOverflowSizeGB: 0.5})

// Adjust write concern for migration
db.collection.insertMany(documents, {writeConcern: {w: 1, j: false}})
```

### Hardware Considerations

- **CPU**: Multi-core processors for parallel processing
- **Memory**: Sufficient RAM for large batch operations
- **Storage**: Fast SSD storage for temporary files
- **Network**: High-bandwidth connections for data transfer

## Integration with CI/CD

### Automated Migration Pipeline

```yaml
# .github/workflows/migration.yml
name: Database Migration
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install -r requirements-migration.txt

      - name: Run migration
        run: |
          python scripts/data_migration/postgresql/data_migration_tool.py migrate \
            --source-db "${{ secrets.SOURCE_DB }}" \
            --target-db "${{ secrets.TARGET_DB }}" \
            --dry-run \
            --report-file migration_report.json

      - name: Validate migration
        run: |
          python scripts/data_migration/validation/data_validator.py validate \
            --db-type postgresql \
            --connection "${{ secrets.TARGET_DB }}" \
            --report-file validation_report.json

      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: migration-reports
          path: |
            migration_report.json
            validation_report.json
```

## Documentation and Support

### Generating Documentation

```bash
# Generate migration documentation
python scripts/data_migration/postgresql/data_migration_tool.py analyze \
  --source-db "postgresql://..." \
  --report-file database_documentation.json
```

### Support Resources

- **Migration Logs**: Check application logs for detailed error information
- **Database Logs**: Review PostgreSQL/MongoDB logs for connection issues
- **Performance Metrics**: Use validation tool to monitor system performance
- **Community Support**: Refer to ComplianceAI documentation and user forums

## Version History

- **v1.0**: Initial migration tools with PostgreSQL and MongoDB support
- **v1.1**: Added comprehensive validation and reporting capabilities
- **v1.2**: Enhanced performance with parallel processing and batch operations
- **v1.3**: Added security features and compliance validation checks
