# Monitoring and Alerting Configuration

This directory contains comprehensive monitoring and alerting configurations for ComplianceAI using Prometheus, Grafana, and Alertmanager.

## Overview

The monitoring setup provides:

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notifications
- **Alert Rules**: Comprehensive alerting rules for all system components

## Directory Structure

```
monitoring/
├── prometheus.yml          # Prometheus configuration
├── alert_rules.yml         # Alert rules definitions
├── alertmanager.yml        # Alertmanager configuration
├── grafana/
│   └── dashboards/
│       └── complianceai-overview.json  # Grafana dashboard
└── README.md               # This file
```

## Prometheus Configuration

### Setup

1. **Install Prometheus:**
   ```bash
   # Using Docker
   docker run -d -p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus

   # Or using package manager
   sudo apt-get install prometheus
   ```

2. **Start Prometheus:**
   ```bash
   ./prometheus --config.file=prometheus.yml
   ```

3. **Access Prometheus:**
   - Web UI: http://localhost:9090
   - Metrics endpoint: http://localhost:9090/metrics

### Configuration Details

The `prometheus.yml` file includes:

- **Scrape Jobs**: For all ComplianceAI services and infrastructure
- **Service Discovery**: Automatic detection of service instances
- **Alert Rules**: Integration with alert_rules.yml
- **Remote Write**: Optional integration with remote monitoring services

### Key Metrics Collected

#### Application Metrics
- HTTP request/response metrics
- Error rates and latency
- Business logic metrics (report generation, validation, etc.)

#### Infrastructure Metrics
- CPU, memory, disk usage
- Network I/O and errors
- System load and process information

#### Database Metrics
- Connection counts and pool status
- Query performance and slow queries
- Database size and growth trends

#### Message Queue Metrics
- Kafka broker status and partition information
- Consumer lag and throughput
- Message processing rates

## Alert Rules

### Categories of Alerts

1. **Infrastructure Alerts**
   - Instance down/unavailable
   - High CPU/memory usage
   - Low disk space
   - Network errors

2. **Database Alerts**
   - Database connection issues
   - High connection counts
   - Slow query performance
   - Replication lag

3. **Application Alerts**
   - Service down/unavailable
   - High error rates
   - Slow response times
   - Memory leaks

4. **Business Logic Alerts**
   - Report generation failures
   - Regulatory deadline breaches
   - Validation errors
   - SLA violations

5. **Security Alerts**
   - Failed login attempts
   - Suspicious activity
   - Certificate expiry warnings

### Alert Severity Levels

- **Critical**: Immediate action required, pages on-call personnel
- **Warning**: Action required within defined timeframe
- **Info**: Informational, no immediate action required

### Customizing Alert Rules

To modify alert rules:

1. **Edit alert_rules.yml:**
   ```yaml
   - alert: CustomAlert
     expr: your_metric > threshold
     for: 5m
     labels:
       severity: warning
     annotations:
       summary: "Custom alert description"
   ```

2. **Reload Prometheus:**
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```

## Alertmanager Configuration

### Setup

1. **Install Alertmanager:**
   ```bash
   # Using Docker
   docker run -d -p 9093:9093 -v $(pwd)/alertmanager.yml:/etc/alertmanager/config.yml prom/alertmanager

   # Or using package manager
   sudo apt-get install prometheus-alertmanager
   ```

2. **Configure Receivers:**
   Update the following placeholders in `alertmanager.yml`:
   ```yaml
   # Email configuration
   smtp_auth_password: '<your-smtp-password>'

   # Slack webhooks
   api_url: '<your-slack-webhook-url>'

   # PagerDuty integration keys
   routing_key: '<your-pagerduty-integration-key>'
   ```

3. **Test Configuration:**
   ```bash
   amtool check-config alertmanager.yml
   ```

### Notification Channels

#### Email Notifications
- Infrastructure alerts → infrastructure@company.com
- Application alerts → application-team@company.com
- Compliance alerts → compliance@company.com
- Security alerts → security@company.com

#### Slack Notifications
- Channel-based routing for different alert types
- Real-time notifications with formatted messages
- Escalation mentions for critical alerts

#### PagerDuty Integration
- Critical alerts trigger immediate paging
- Automatic escalation based on alert severity
- Integration with on-call schedules

### Alert Grouping and Routing

Alerts are grouped by:
- Alert name and severity
- Service and instance
- Category (infrastructure, application, business, etc.)

Routes are configured for:
- **Critical alerts**: Immediate paging via PagerDuty
- **Infrastructure alerts**: Infrastructure team via email/Slack
- **Application alerts**: Application team via email/Slack
- **Business alerts**: Compliance team with high priority
- **Security alerts**: Security team with immediate escalation

## Grafana Dashboards

### Setup

1. **Install Grafana:**
   ```bash
   # Using Docker
   docker run -d -p 3000:3000 grafana/grafana

   # Or using package manager
   sudo apt-get install grafana
   ```

2. **Configure Data Source:**
   - URL: http://prometheus:9090
   - Access: Server (default)
   - Scrape interval: 15s

3. **Import Dashboard:**
   ```bash
   # Via API
   curl -X POST -H "Content-Type: application/json" \
     -d @complianceai-overview.json \
     http://admin:admin@localhost:3000/api/dashboards/db
   ```

### Dashboard Panels

#### System Health
- Service status indicators
- Active alerts overview
- System resource usage

#### Performance Metrics
- HTTP request rates and latency
- Database connection counts
- Message queue throughput

#### Business Metrics
- Report generation status
- Regulatory deadlines
- Error rates by service

#### Infrastructure Metrics
- CPU and memory usage
- Disk space utilization
- Network I/O statistics

### Customizing Dashboards

To modify dashboards:

1. **Edit JSON file:**
   Update `complianceai-overview.json` with new panels or metrics

2. **Reload dashboard:**
   ```bash
   curl -X POST http://localhost:3000/api/admin/provisioning/dashboards/reload
   ```

## Monitoring Best Practices

### Metrics Collection

1. **Use appropriate metric types:**
   - Counters: For cumulative values (requests served)
   - Gauges: For point-in-time values (current memory usage)
   - Histograms: For latency and response time distributions

2. **Follow naming conventions:**
   - `complianceai_<component>_<metric>_<type>`
   - Use snake_case for metric names
   - Include relevant labels (service, instance, status, etc.)

3. **Set appropriate scrape intervals:**
   - Critical metrics: 15-30 seconds
   - Business metrics: 30-60 seconds
   - Infrastructure metrics: 30-60 seconds

### Alert Design

1. **Avoid alert fatigue:**
   - Use appropriate thresholds
   - Implement alert inhibition
   - Group related alerts
   - Use different severity levels

2. **Include actionable information:**
   - Clear alert descriptions
   - Runbook URLs
   - Contact information
   - Escalation procedures

3. **Test alert configurations:**
   - Use alert testing tools
   - Validate notification channels
   - Test escalation procedures

### Dashboard Organization

1. **Logical grouping:**
   - System health overview
   - Service-specific metrics
   - Business KPIs
   - Infrastructure monitoring

2. **Consistent time ranges:**
   - Default: Last 1 hour
   - Options: 5m, 15m, 1h, 6h, 24h, 7d

3. **Template variables:**
   - Instance selection
   - Service filtering
   - Time range customization

## Troubleshooting Monitoring

### Prometheus Issues

**High memory usage:**
```bash
# Check Prometheus memory usage
ps aux | grep prometheus

# Reduce retention time
--storage.tsdb.retention.time=200h

# Increase memory limits
--storage.tsdb.max-block-duration=2h
```

**Missing metrics:**
```bash
# Check service endpoints
curl http://service:port/metrics

# Verify scrape configuration
curl http://localhost:9090/config

# Check Prometheus logs
docker logs prometheus
```

### Alertmanager Issues

**Alerts not firing:**
```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules

# Validate alert expressions
curl http://localhost:9090/api/v1/query?query=your_alert_expression

# Check Alertmanager logs
docker logs alertmanager
```

**Notifications not sent:**
```bash
# Test notification channels
curl -X POST http://localhost:9093/api/v1/alerts -d '[{"labels": {"alertname": "TestAlert"}}]'

# Check SMTP configuration
telnet smtp.company.com 587

# Verify webhook URLs
curl -X POST -H 'Content-type: application/json' --data '{"text":"Test"}' YOUR_SLACK_WEBHOOK
```

### Grafana Issues

**Dashboard not loading:**
```bash
# Check Grafana logs
docker logs grafana

# Verify data source configuration
curl http://admin:admin@localhost:3000/api/datasources

# Test Prometheus connectivity
curl http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=up
```

**Panels showing no data:**
```bash
# Check metric names
curl http://localhost:9090/api/v1/label/__name__/values

# Verify query syntax
curl "http://localhost:9090/api/v1/query?query=your_metric"

# Check time range settings
# Ensure query time range matches data retention
```

## Integration Examples

### Application Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
REQUEST_COUNT = Counter('complianceai_http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('complianceai_http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('complianceai_active_connections', 'Number of active connections')

# Use metrics
REQUEST_COUNT.labels(method='GET', endpoint='/api/reports', status='200').inc()
with REQUEST_LATENCY.labels(method='POST', endpoint='/api/submit').time():
    # Your code here
    pass
ACTIVE_CONNECTIONS.set(42)
```

### Custom Business Metrics

```python
from prometheus_client import Counter, Gauge

# Business logic metrics
REPORT_GENERATION_SUCCESS = Counter('complianceai_report_generation_success_total', 'Successful report generations')
REPORT_GENERATION_FAILURE = Counter('complianceai_report_generation_failure_total', 'Failed report generations')
REGULATORY_DEADLINE_HOURS = Gauge('complianceai_regulatory_deadline_hours_remaining', 'Hours remaining until deadline', ['report_type'])

# Update metrics
REPORT_GENERATION_SUCCESS.inc()
REGULATORY_DEADLINE_HOURS.labels(report_type='FINREP').set(48)
```

## Scaling Considerations

### Horizontal Scaling

**Prometheus Federation:**
```yaml
# Add to prometheus.yml
scrape_configs:
  - job_name: 'federate'
    scrape_interval: 15s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="complianceai"}'
    static_configs:
      - targets:
        - 'source-prometheus-1:9090'
        - 'source-prometheus-2:9090'
```

**Alertmanager Clustering:**
```bash
# Run multiple Alertmanager instances
--cluster.listen-address=0.0.0.0:9094
--cluster.peer=alertmanager-1:9094
--cluster.peer=alertmanager-2:9094
```

### High Availability

**Prometheus HA:**
- Run multiple Prometheus instances
- Use service discovery for targets
- Implement alert deduplication

**Grafana HA:**
- Use load balancer for multiple Grafana instances
- Shared database for dashboards and users
- Synchronized configuration files

## Security Considerations

### Network Security

- Restrict Prometheus and Grafana access to internal networks
- Use TLS for all external communications
- Implement authentication and authorization

### Data Protection

- Encrypt sensitive metrics data
- Implement access controls for dashboards
- Regular backup of monitoring configuration

### Compliance

- Audit all monitoring access and changes
- Implement data retention policies
- Regular security assessments of monitoring infrastructure

## Maintenance Procedures

### Regular Tasks

**Daily:**
- Review active alerts
- Check system health dashboards
- Verify backup completion

**Weekly:**
- Review alerting rules effectiveness
- Update dashboard layouts
- Clean up old metrics data

**Monthly:**
- Performance optimization review
- Security patch updates
- Documentation updates

### Backup and Recovery

**Configuration Backup:**
```bash
# Backup configurations
tar -czf monitoring-backup-$(date +%Y%m%d).tar.gz \
  prometheus.yml \
  alert_rules.yml \
  alertmanager.yml \
  grafana/dashboards/
```

**Metrics Data Backup:**
```bash
# Backup Prometheus data
docker run --rm -v prometheus_data:/prometheus \
  -v $(pwd):/backup \
  busybox tar czf /backup/prometheus-data-$(date +%Y%m%d).tar.gz /prometheus
```

## Support and Resources

- **Documentation**: Refer to official Prometheus, Grafana, and Alertmanager documentation
- **Community**: Prometheus, Grafana, and Alertmanager user communities
- **Professional Services**: Commercial support options available
- **Training**: Official training courses and certifications

## Version History

- **v1.0**: Initial monitoring and alerting setup
- **v1.1**: Enhanced business metrics and alerting rules
- **v1.2**: Added Grafana dashboards and improved alerting
- **v1.3**: Implemented security hardening and compliance features
