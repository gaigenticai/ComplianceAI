# Production Deployment Configurations

This directory contains comprehensive deployment configurations for ComplianceAI across different environments and platforms.

## Overview

The deployment configurations are organized as follows:

- `docker-compose.prod.yml` - Production-ready Docker Compose setup
- `kubernetes-prod.yml` - Kubernetes production manifests
- `production.env` - Production environment variables
- `staging.env` - Staging environment variables

## Docker Compose Production Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 16GB RAM
- 100GB free disk space
- Linux/Windows/MacOS host

### Quick Start

1. **Clone and navigate to the deployment directory:**
   ```bash
   cd /path/to/complianceai/configs/deployment
   ```

2. **Set environment variables:**
   ```bash
   export BUILD_NUMBER=v1.0.0
   export DB_PASSWORD=your_secure_db_password
   export MONGO_PASSWORD=your_secure_mongo_password
   export JWT_SECRET_KEY=your_256_bit_jwt_secret
   export ENCRYPTION_KEY=your_256_bit_encryption_key
   export GRAFANA_PASSWORD=your_secure_grafana_password
   ```

3. **Deploy the stack:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify deployment:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   docker-compose -f docker-compose.prod.yml logs -f web-interface
   ```

### Configuration Options

#### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| BUILD_NUMBER | Docker image tag version | Yes | - |
| DB_PASSWORD | PostgreSQL password | Yes | - |
| MONGO_PASSWORD | MongoDB password | Yes | - |
| JWT_SECRET_KEY | JWT signing secret (256-bit) | Yes | - |
| ENCRYPTION_KEY | Data encryption key (256-bit) | Yes | - |
| GRAFANA_PASSWORD | Grafana admin password | Yes | - |

#### Service Configuration

Each service can be configured via environment variables in the Docker Compose file:

```yaml
web-interface:
  environment:
    - LOG_LEVEL=INFO
    - MAX_CONCURRENT_REPORTS=5
    - REPORT_GENERATION_TIMEOUT=3600
```

### Scaling Services

#### Horizontal Scaling

Scale web interface instances:
```bash
docker-compose -f docker-compose.prod.yml up -d --scale web-interface=5
```

Scale Kafka brokers:
```bash
docker-compose -f docker-compose.prod.yml up -d --scale kafka=3
```

#### Vertical Scaling

Update resource limits in the compose file:
```yaml
web-interface:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '1.0'
        memory: 1G
```

### Monitoring and Logs

#### Health Checks

Check service health:
```bash
docker-compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

#### View Logs

View all service logs:
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

View specific service logs:
```bash
docker-compose -f docker-compose.prod.yml logs -f web-interface
```

#### Metrics

Access Prometheus metrics:
```bash
curl http://localhost:9090
```

Access Grafana dashboard:
```bash
# Default credentials: admin / GRAFANA_PASSWORD
open http://localhost:3000
```

### Backup and Recovery

#### Automated Backups

Backups are configured to run daily at 2 AM. View backup status:
```bash
docker-compose -f docker-compose.prod.yml logs backup
```

#### Manual Backup

Create immediate backup:
```bash
docker-compose -f docker-compose.prod.yml exec backup /app/backup.sh
```

#### Restore from Backup

1. Stop services:
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

2. Restore databases:
   ```bash
   docker-compose -f docker-compose.prod.yml exec postgres /app/restore.sh
   ```

3. Start services:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Security Considerations

#### Network Security

- All services communicate over an isolated Docker network
- External access is restricted to nginx (ports 80/443)
- Internal services are not exposed externally

#### Secrets Management

- Database passwords are passed via environment variables
- JWT secrets and encryption keys must be securely generated
- Consider using Docker secrets or external secret management

#### SSL/TLS Configuration

SSL certificates are expected to be mounted at `/etc/nginx/ssl/`:
```bash
# Generate self-signed certificate for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/tls.key -out ssl/tls.crt
```

### Troubleshooting

#### Common Issues

**Port conflicts:**
```bash
# Check port usage
netstat -tlnp | grep :80
netstat -tlnp | grep :443

# Stop conflicting services or change ports in compose file
```

**Out of memory:**
```bash
# Check memory usage
docker stats

# Increase Docker memory limit or reduce service resource limits
```

**Service startup failures:**
```bash
# Check service logs
docker-compose -f docker-compose.prod.yml logs <service-name>

# Verify environment variables are set
docker-compose -f docker-compose.prod.yml config
```

## Kubernetes Production Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (optional)
- 16GB RAM cluster
- 100GB storage per node

### Quick Start

1. **Set up namespace:**
   ```bash
   kubectl create namespace complianceai-prod
   ```

2. **Create secrets:**
   ```bash
   # Create secrets from environment variables
   kubectl create secret generic complianceai-secrets \
     --from-literal=db-password=$DB_PASSWORD \
     --from-literal=mongo-password=$MONGO_PASSWORD \
     --from-literal=jwt-secret-key=$JWT_SECRET_KEY \
     --from-literal=encryption-key=$ENCRYPTION_KEY \
     --from-literal=grafana-password=$GRAFANA_PASSWORD \
     --namespace complianceai-prod
   ```

3. **Deploy the application:**
   ```bash
   kubectl apply -f kubernetes-prod.yml
   ```

4. **Verify deployment:**
   ```bash
   kubectl get pods -n complianceai-prod
   kubectl get services -n complianceai-prod
   kubectl get ingress -n complianceai-prod
   ```

### Configuration Management

#### ConfigMaps

Application configuration is managed via ConfigMaps:
```bash
# View current configuration
kubectl get configmap complianceai-config -n complianceai-prod -o yaml

# Update configuration
kubectl edit configmap complianceai-config -n complianceai-prod
```

#### Secrets

Sensitive data is stored in Kubernetes secrets:
```bash
# View secret keys (values are base64 encoded)
kubectl get secret complianceai-secrets -n complianceai-prod -o yaml

# Update a secret
kubectl patch secret complianceai-secrets -n complianceai-prod \
  --type='json' -p='[{"op": "replace", "path": "/data/new-key", "value": "base64-value"}]'
```

### Scaling and Updates

#### Horizontal Pod Autoscaling

Enable HPA for web interface:
```bash
kubectl autoscale deployment complianceai-web \
  --cpu-percent=70 \
  --min=3 \
  --max=10 \
  --namespace complianceai-prod
```

#### Rolling Updates

Update application image:
```bash
kubectl set image deployment/complianceai-web web-interface=complianceai/web-interface:v1.1.0 \
  --namespace complianceai-prod
```

Monitor rollout:
```bash
kubectl rollout status deployment/complianceai-web -n complianceai-prod
```

### Storage Management

#### Persistent Volumes

Check PV status:
```bash
kubectl get pv
kubectl get pvc -n complianceai-prod
```

#### Storage Expansion

Expand PostgreSQL storage:
```bash
kubectl patch pvc postgres-pvc \
  --patch '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}' \
  --namespace complianceai-prod
```

### Networking and Ingress

#### External Access

The deployment includes an Ingress resource for external access. Update the host:
```bash
kubectl patch ingress complianceai-ingress \
  --patch '{"spec":{"rules":[{"host":"your-domain.com"}]}}' \
  --namespace complianceai-prod
```

#### SSL/TLS Certificates

Certificates are managed via cert-manager. Install cert-manager first:
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.11.0/cert-manager.yaml
```

### Monitoring and Observability

#### Prometheus Metrics

Access Prometheus:
```bash
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
open http://localhost:9090
```

#### Grafana Dashboards

Access Grafana:
```bash
kubectl port-forward svc/grafana 3000:3000 -n monitoring
# Login with admin/GRAFANA_PASSWORD
```

#### Application Metrics

View application metrics:
```bash
kubectl port-forward svc/complianceai-web 8000:8000 -n complianceai-prod
curl http://localhost:8000/metrics
```

### Backup and Disaster Recovery

#### Automated Backups

Backups are scheduled via CronJobs. View backup jobs:
```bash
kubectl get cronjob -n complianceai-prod
kubectl get jobs -n complianceai-prod
```

#### Manual Backup

Execute manual backup:
```bash
kubectl create job manual-backup \
  --from=cronjob/complianceai-backup \
  --namespace complianceai-prod
```

#### Disaster Recovery

For disaster recovery:

1. **Backup current state:**
   ```bash
   kubectl get all -n complianceai-prod -o yaml > disaster-recovery-backup.yaml
   ```

2. **Restore from backup:**
   ```bash
   kubectl apply -f disaster-recovery-backup.yaml
   ```

### Security Hardening

#### Pod Security Standards

Apply security policies:
```bash
kubectl apply -f pod-security-policy.yaml
```

#### Network Policies

Restrict pod-to-pod communication:
```bash
kubectl apply -f network-policies.yaml
```

#### RBAC Configuration

Review service account permissions:
```bash
kubectl get rolebindings -n complianceai-prod
kubectl describe role complianceai-role -n complianceai-prod
```

## Environment-Specific Configurations

### Production Environment

The `production.env` file contains settings optimized for:

- High availability (3+ replicas)
- Maximum security
- Performance optimization
- Comprehensive monitoring
- Regulatory compliance

### Staging Environment

The `staging.env` file contains settings for:

- Testing and validation
- Reduced resource allocation
- Sandbox API endpoints
- Relaxed security for development

### Environment Variables Reference

#### Database Configuration

```bash
# PostgreSQL
DB_HOST=complianceai-postgres
DB_PORT=5432
DB_NAME=complianceai_prod
DB_USER=complianceai
DB_PASSWORD=<secure-password>
DB_SSL_MODE=require
DB_MAX_CONNECTIONS=200

# MongoDB
MONGODB_HOST=complianceai-mongodb
MONGODB_DB=complianceai_prod
MONGODB_USER=complianceai
MONGODB_PASSWORD=<secure-password>
MONGODB_SSL=true

# Redis
REDIS_HOST=complianceai-redis
REDIS_PASSWORD=<secure-password>
REDIS_SSL=true
```

#### Security Configuration

```bash
# Encryption keys (generate 256-bit keys)
JWT_SECRET_KEY=<base64-encoded-256-bit-key>
ENCRYPTION_KEY=<base64-encoded-256-bit-key>
AES_ENCRYPTION_KEY=<base64-encoded-256-bit-key>

# OAuth2 (if applicable)
OAUTH2_CLIENT_ID=<oauth-client-id>
OAUTH2_CLIENT_SECRET=<oauth-client-secret>
```

#### External Integrations

```bash
# Regulatory APIs
EBA_CLIENT_ID=<eba-client-id>
EBA_CLIENT_SECRET=<eba-client-secret>
FEDERAL_RESERVE_API_KEY=<frb-api-key>

# SFTP
SFTP_HOST=<sftp-host>
SFTP_USERNAME=<sftp-username>
SFTP_KEY_PATH=<path-to-private-key>
```

## Troubleshooting Deployment Issues

### Docker Compose Issues

**Service fails to start:**
```bash
# Check service logs
docker-compose -f docker-compose.prod.yml logs <service-name>

# Check service configuration
docker-compose -f docker-compose.prod.yml config

# Verify environment variables
docker-compose -f docker-compose.prod.yml exec <service-name> env
```

**Database connection issues:**
```bash
# Test database connectivity
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U complianceai

# Check database logs
docker-compose -f docker-compose.prod.yml logs postgres
```

### Kubernetes Issues

**Pod fails to start:**
```bash
# Check pod status
kubectl describe pod <pod-name> -n complianceai-prod

# Check pod logs
kubectl logs <pod-name> -n complianceai-prod

# Check events
kubectl get events -n complianceai-prod
```

**Service unreachable:**
```bash
# Check service endpoints
kubectl get endpoints -n complianceai-prod

# Check service configuration
kubectl describe service <service-name> -n complianceai-prod
```

**Storage issues:**
```bash
# Check PVC status
kubectl describe pvc <pvc-name> -n complianceai-prod

# Check PV status
kubectl describe pv <pv-name>
```

## Performance Optimization

### Resource Allocation

Monitor and adjust resource requests/limits:
```bash
kubectl top pods -n complianceai-prod
kubectl top nodes
```

### Database Optimization

Tune PostgreSQL parameters:
```yaml
# In kubernetes-prod.yml, update postgres deployment
env:
- name: POSTGRES_SHARED_BUFFERS
  value: "512MB"
- name: POSTGRES_EFFECTIVE_CACHE_SIZE
  value: "1536MB"
- name: POSTGRES_MAINTENANCE_WORK_MEM
  value: "128MB"
```

### Caching Strategy

Configure Redis for optimal performance:
```yaml
# In kubernetes-prod.yml, update redis deployment
env:
- name: REDIS_MAXMEMORY
  value: "512mb"
- name: REDIS_MAXMEMORY_POLICY
  value: "allkeys-lru"
```

## Backup and Recovery Procedures

### Automated Backups

Daily backups are configured. Monitor backup jobs:
```bash
kubectl get cronjob -n complianceai-prod
kubectl logs job/<backup-job-name> -n complianceai-prod
```

### Point-in-Time Recovery

For PostgreSQL PITR:
```bash
# Restore to specific timestamp
kubectl exec -it complianceai-postgres-0 -n complianceai-prod -- \
  pg_restore --dbname=complianceai_prod --create /backup/backup.sql
```

### Cross-Region Disaster Recovery

Set up cross-region replication:
```yaml
# Configure PostgreSQL replication
env:
- name: POSTGRES_REPLICATION_MODE
  value: "slave"
- name: POSTGRES_MASTER_HOST
  value: "postgres-primary.external-region.com"
```

## Security Best Practices

### Secret Management

Use external secret management:
```bash
# Install external-secrets operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets
```

### Network Security

Apply network policies:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: complianceai-network-policy
  namespace: complianceai-prod
spec:
  podSelector:
    matchLabels:
      app: complianceai
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: complianceai
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: complianceai
  - to: []  # Deny all other egress
```

### Compliance and Auditing

Enable audit logging:
```yaml
# In kubernetes-prod.yml
spec:
  containers:
  - name: web-interface
    securityContext:
      audit: "true"
      auditWrite: "true"
```

## Support and Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Review monitoring dashboards
- Check backup completion
- Update security patches
- Review error logs

**Monthly:**
- Performance optimization review
- Security vulnerability assessment
- Database maintenance (VACUUM, REINDEX)
- Certificate renewal check

**Quarterly:**
- Full security audit
- Disaster recovery testing
- Performance benchmarking
- Regulatory compliance review

### Getting Help

- **Documentation:** Refer to main ComplianceAI documentation
- **Support Portal:** support.company.com
- **Emergency Contact:** +1-555-0199 (24/7)
- **Community:** complianceai-users@company.com

## Version History

- **v1.0**: Initial production deployment configurations
- **v1.1**: Added Kubernetes manifests and security hardening
- **v1.2**: Enhanced monitoring and backup configurations
- **v1.3**: Added disaster recovery and performance optimization
