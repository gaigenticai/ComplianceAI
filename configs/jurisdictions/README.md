# Jurisdiction Configuration Guide

This directory contains sample configuration files for different regulatory jurisdictions supported by ComplianceAI.

## Overview

Jurisdiction configurations define how the system handles regulatory compliance for specific geographic regions. Each configuration includes:

- Regulatory authorities and their APIs
- Report types and templates
- Validation rules and business logic
- Submission channels and deadlines
- Compliance calendars and holidays
- Security and encryption settings
- Performance and monitoring parameters

## Available Configurations

### Base Configuration (`base_jurisdiction.yaml`)
- **Purpose**: Template for creating new jurisdiction configurations
- **Usage**: Copy this file and customize for your specific jurisdiction
- **Contains**: All possible configuration options with default values

### European Union (`eu_jurisdiction.yaml`)
- **Regulatory Bodies**: EBA, ECB, ESMA, EIOPA
- **Key Reports**: FINREP, COREP, DORA, PSD2
- **Standards**: IFRS, XBRL 3.1
- **Currency**: EUR
- **Timezone**: Europe/Brussels

### United Kingdom (`uk_jurisdiction.yaml`)
- **Regulatory Bodies**: FCA, PRA, Bank of England, HM Treasury
- **Key Reports**: FINREP UK, COREP UK, FS45, SMCR
- **Standards**: UK GAAP, XBRL 1.0
- **Currency**: GBP
- **Timezone**: Europe/London

### United States (`us_jurisdiction.yaml`)
- **Regulatory Bodies**: Federal Reserve, OCC, FDIC, CFPB
- **Key Reports**: FFIEC 031, Y-9C, FR Y-14, CCAR
- **Standards**: US GAAP, XBRL 2.0
- **Currency**: USD
- **Timezone**: America/New_York

## Configuration Structure

Each jurisdiction configuration follows this structure:

```yaml
jurisdiction:
  # Basic information
  id: "UNIQUE_ID"
  name: "Display Name"
  code: "ISO_CODE"
  region: "CONTINENT"
  timezone: "IANA_TIMEZONE"

  # Regulatory authorities
  authorities:
    - id: "authority_id"
      name: "Full Authority Name"
      website: "https://authority.example.com"
      api_endpoint: "https://api.authority.example.com"

  # Report definitions
  reports:
    - id: "REPORT_ID"
      name: "Report Display Name"
      frequency: "quarterly|annual"
      format: "XBRL|JSON|CSV|XML"
      mandatory: true|false

  # Validation rules
  validation:
    business_rules:
      - id: "rule_id"
        name: "Rule Description"
        expression: "mathematical_expression"
        severity: "critical|error|warning"
        enabled: true|false

  # Submission settings
  submission:
    channels:
      - type: "API|SFTP"
        primary: true|false
        endpoint: "submission_url"
        authentication: "oauth2|ssh_key|api_key"

    deadlines:
      - report_type: "REPORT_ID"
        frequency: "quarterly|annual"
        offset_days: 45
        grace_period_days: 15

  # Calendar and holidays
  calendar:
    holidays:
      - name: "Holiday Name"
        date: "MM-DD"
        type: "fixed|dynamic"

  # Security configuration
  security:
    encryption:
      algorithm: "AES-256-GCM"
      key_rotation_days: 90

    digital_signatures:
      algorithm: "RSA-PSS"
      key_size: 4096

  # Performance settings
  performance:
    report_generation_timeout: 3600
    max_concurrent_reports: 5

  # Monitoring configuration
  monitoring:
    metrics:
      - name: "metric_name"
        threshold: 100
        alert: true
```

## How to Use

### 1. Select or Create Configuration

Choose an existing configuration or create a new one:

```bash
# Copy base template
cp base_jurisdiction.yaml my_jurisdiction.yaml

# Edit configuration
nano my_jurisdiction.yaml
```

### 2. Configure System

Update your main configuration to use the jurisdiction:

```yaml
# In your main config file
compliance:
  jurisdictions:
    - id: "EU"
      config_file: "configs/jurisdictions/eu_jurisdiction.yaml"
      enabled: true
      primary: true
```

### 3. Validate Configuration

Test your configuration before deployment:

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('eu_jurisdiction.yaml'))"

# Test configuration loading
python -m complianceai.config validate eu_jurisdiction.yaml
```

### 4. Deploy Configuration

Apply the configuration to your system:

```bash
# Restart services to pick up new configuration
docker-compose restart complianceai

# Or reload configuration dynamically
curl -X POST http://localhost:8000/api/config/reload
```

## Customization Guidelines

### Adding New Jurisdictions

1. **Copy Base Template**: Start with `base_jurisdiction.yaml`
2. **Set Basic Information**: Update id, name, code, region, timezone
3. **Configure Authorities**: Add relevant regulatory bodies
4. **Define Reports**: Specify required report types and formats
5. **Set Validation Rules**: Add jurisdiction-specific business rules
6. **Configure Submission**: Set up appropriate submission channels
7. **Define Calendar**: Configure holidays and business days
8. **Set Security**: Configure encryption and authentication
9. **Tune Performance**: Adjust timeouts and limits for your scale

### Regulatory Updates

Regularly update configurations for:

- **New Regulations**: Add new report types and validation rules
- **Changed Deadlines**: Update submission deadlines and grace periods
- **API Changes**: Modify endpoint URLs and authentication methods
- **Security Updates**: Update encryption algorithms and key rotation policies

### Multi-Jurisdiction Setup

For institutions operating in multiple jurisdictions:

```yaml
compliance:
  jurisdictions:
    - id: "EU"
      config_file: "eu_jurisdiction.yaml"
      enabled: true
      primary: false

    - id: "UK"
      config_file: "uk_jurisdiction.yaml"
      enabled: true
      primary: true  # Primary jurisdiction

    - id: "US"
      config_file: "us_jurisdiction.yaml"
      enabled: false  # Disabled for now
```

## Validation Rules

### Business Rule Expressions

Use these operators in validation expressions:

- **Arithmetic**: `+`, `-`, `*`, `/`
- **Comparison**: `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Logical**: `and`, `or`, `not`
- **Functions**: `sum()`, `avg()`, `min()`, `max()`, `count()`
- **Fields**: Reference data fields by name (e.g., `total_assets`, `total_liabilities`)

### Example Rules

```yaml
business_rules:
  - id: "balance_sheet"
    expression: "total_assets == total_liabilities + total_equity"
    severity: "critical"

  - id: "capital_adequacy"
    expression: "cet1_ratio >= 4.5 and total_capital_ratio >= 8.0"
    severity: "critical"

  - id: "large_exposure"
    expression: "max_customer_exposure <= tier1_capital * 0.25"
    severity: "error"
```

## Security Considerations

### Encryption Settings

```yaml
security:
  encryption:
    algorithm: "AES-256-GCM"  # Recommended
    key_rotation_days: 90     # Maximum 90 days
    key_management: "HSM"     # Hardware Security Module
```

### Authentication Methods

```yaml
submission:
  channels:
    - type: "API"
      authentication: "oauth2_client_credentials"
    - type: "SFTP"
      authentication: "ssh_key"
```

### Access Control

```yaml
access_control:
  rbac_enabled: true
  mfa_required: true
  session_timeout_minutes: 30
```

## Performance Tuning

### Timeout Settings

```yaml
performance:
  report_generation_timeout: 3600    # 1 hour
  api_timeout: 300                   # 5 minutes
  database_timeout: 60               # 1 minute
```

### Resource Limits

```yaml
performance:
  max_concurrent_reports: 5
  max_memory_usage_gb: 16
  max_cpu_usage_percent: 80
```

## Monitoring and Alerts

### Key Metrics

```yaml
monitoring:
  metrics:
    - name: "report_generation_time"
      threshold: 1800
      alert: true
    - name: "submission_success_rate"
      threshold: 99.5
      alert: true
```

### Health Checks

```yaml
health_checks:
  - name: "regulator_api"
    url: "https://api.regulator.example.com/health"
    interval_seconds: 300
    timeout_seconds: 10
```

## Troubleshooting

### Common Issues

1. **Configuration Loading Errors**
   - Check YAML syntax
   - Verify file permissions
   - Ensure all required fields are present

2. **Validation Failures**
   - Review validation expressions
   - Check data field mappings
   - Verify reference data availability

3. **Submission Errors**
   - Test network connectivity
   - Verify authentication credentials
   - Check regulatory API status

4. **Performance Issues**
   - Monitor resource usage
   - Review database query performance
   - Check for memory leaks

### Logs and Debugging

Enable debug logging for troubleshooting:

```yaml
logging:
  level: "DEBUG"
  file: "/var/log/complianceai/debug.log"
  max_size: "100MB"
  retention: 30
```

## Support and Updates

- **Documentation**: Refer to the main ComplianceAI documentation
- **Support**: Contact compliance-support@company.com
- **Updates**: Check for regulatory updates quarterly
- **Training**: Schedule annual configuration review training

## Version History

- **v1.0**: Initial jurisdiction configurations (EU, UK, US)
- **v1.1**: Added DORA and SMCR support
- **v1.2**: Enhanced security configurations
- **v1.3**: Improved performance settings
