# KYC Automation Platform - Shell Scripts Documentation

This directory contains comprehensive shell scripts for managing the KYC Automation Platform. These scripts provide a complete solution for starting, stopping, and monitoring all services.

## 📋 Available Scripts

### 🚀 Startup Scripts

#### 1. `start-kyc-simple.sh` (Recommended for macOS)
**Compatible with all bash versions including macOS default**

```bash
./start-kyc-simple.sh [OPTIONS]
```

**Features:**
- ✅ Cross-platform compatibility (macOS, Linux, Windows WSL)
- ✅ Automatic port conflict resolution
- ✅ Service health monitoring
- ✅ Comprehensive error handling
- ✅ Real-time status updates
- ✅ Graceful cleanup on exit

**Options:**
- `--help` - Show usage information
- `--check-only` - Only validate prerequisites and configuration

#### 2. `start-kyc-platform.sh` (Advanced - Requires Bash 4.0+)
**Full-featured version with associative arrays**

```bash
./start-kyc-platform.sh [OPTIONS]
```

**Additional Features:**
- 🔧 Advanced service tracking
- 📊 Enhanced monitoring capabilities
- 🎯 More detailed status reporting

**Options:**
- `--help` - Show usage information
- `--no-monitoring` - Skip Prometheus/Grafana
- `--dev-mode` - Enable debug logging
- `--check-only` - Only check prerequisites

### 🛑 Stop Scripts

#### `stop-kyc-platform.sh`
**Graceful service shutdown**

```bash
./stop-kyc-platform.sh [COMMAND]
```

**Commands:**
- `stop` - Graceful shutdown (default)
- `force` - Force kill all services
- `status` - Show running services
- `help` - Show help message

### 📊 Status Scripts

#### 1. `check-kyc-status-simple.sh` (Recommended)
**Compatible with all bash versions**

```bash
./check-kyc-status-simple.sh [COMMAND]
```

#### 2. `check-kyc-status.sh` (Advanced)
**Full-featured version with enhanced reporting**

```bash
./check-kyc-status.sh [COMMAND]
```

**Commands for both:**
- `status` - Basic service status (default)
- `full` - Detailed status with system resources
- `logs` - Show log information
- `resources` - System resource usage
- `urls` - Quick access URLs

## 🎯 Quick Start Guide

### 1. Start the Platform
```bash
# Simple version (recommended for macOS)
./start-kyc-simple.sh

# Advanced version (Linux with Bash 4.0+)
./start-kyc-platform.sh
```

### 2. Check Status
```bash
# Basic status
./check-kyc-status-simple.sh

# Detailed status
./check-kyc-status-simple.sh full
```

### 3. Stop the Platform
```bash
# Graceful stop
./stop-kyc-platform.sh

# Force stop
./stop-kyc-platform.sh force
```

## 🏗️ What Gets Started

### Infrastructure Services
- **Kafka** (Port 9092) - Message broker for inter-service communication
- **Zookeeper** (Port 2181) - Kafka coordination service
- **Pinecone** (Port 8080) - Vector database for KYC data

### Python Agent Services
- **OCR Agent** (Port 8001) - Document text extraction
- **Face Agent** (Port 8002) - Facial recognition and liveness detection
- **Watchlist Agent** (Port 8003) - Sanctions and PEP screening
- **Data Integration Agent** (Port 8004) - External API integrations
- **QA Agent** (Port 8005) - Quality assurance and validation

### Core Services
- **Rust Core** (Port 8000) - Main orchestrator and web UI

### Optional Monitoring
- **Prometheus** (Port 9090) - Metrics collection
- **Grafana** (Port 3000) - Monitoring dashboards

## 🔧 Configuration

### Environment Variables
The scripts automatically create a `.env` file from `.env.example` if it doesn't exist. Key variables:

```bash
# Authentication
REQUIRE_AUTH=false              # Set to true for production

# Core Configuration
RUST_LOG=info                   # Log level
SERVER_HOST=0.0.0.0            # Server bind address
SERVER_PORT=8000               # Main server port

# External API Keys (required for production)
OFAC_API_KEY=your-key-here
EXPERIAN_API_KEY=your-key-here
# ... (see .env.example for complete list)
```

### Port Configuration
The scripts automatically resolve port conflicts. If default ports are in use, they will find the next available ports and update the configuration accordingly.

**Default Ports:**
- Rust Core: 8000
- OCR Agent: 8001
- Face Agent: 8002
- Watchlist Agent: 8003
- Data Integration: 8004
- QA Agent: 8005

## 📁 Directory Structure Created

```
ComplianceAI/
├── logs/                       # Service logs
│   ├── infrastructure/         # Docker service logs
│   ├── agents/                 # Python agent logs
│   ├── core/                   # Rust core logs
│   └── monitoring/             # Monitoring logs
├── pids/                       # Process ID files
├── .env                        # Environment variables
└── python-agents/*/venv/       # Virtual environments (auto-created)
```

## 🧪 Testing the Platform

### 1. Web Interface
Once started, access the platform at:
- **Main UI**: http://localhost:8000
- **User Guide**: http://localhost:8000/userguide
- **API Stats**: http://localhost:8000/api/stats
- **Health Check**: http://localhost:8000/health

### 2. API Testing
```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8001/health  # OCR Agent
curl http://localhost:8002/health  # Face Agent
# ... etc for other agents

# System statistics
curl http://localhost:8000/api/stats
```

### 3. Service Status
```bash
# Quick status check
./check-kyc-status-simple.sh

# Detailed system information
./check-kyc-status-simple.sh full
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Permission Denied
```bash
chmod +x *.sh
```

#### 2. Port Conflicts
The scripts automatically resolve port conflicts, but you can check current assignments:
```bash
./check-kyc-status-simple.sh
```

#### 3. Docker Issues
```bash
# Check Docker status
docker info

# Restart Docker services
docker-compose down
docker-compose up -d
```

#### 4. Python Dependencies
```bash
# If Python agents fail to start, clean virtual environments
rm -rf python-agents/*/venv
./start-kyc-simple.sh
```

#### 5. Rust Build Issues
```bash
cd rust-core
cargo clean
cargo build --release
cd ..
./start-kyc-simple.sh
```

### Log Analysis
```bash
# View recent logs
./check-kyc-status-simple.sh logs

# View specific service logs
tail -f logs/core/rust-core.log
tail -f logs/agents/ocr-agent.log

# Search for errors
grep -r "ERROR\|FATAL" logs/
```

### Service Recovery
```bash
# Force stop and restart
./stop-kyc-platform.sh force
./start-kyc-simple.sh
```

## 🔒 Security Considerations

### Development vs Production

**Development Mode (Default):**
- `REQUIRE_AUTH=false` - No authentication required
- Mock API keys work for testing
- Debug logging enabled

**Production Mode:**
- Set `REQUIRE_AUTH=true`
- Configure real API keys in `.env`
- Set appropriate log levels
- Enable monitoring and alerting

### API Keys
For production deployment, configure real API keys:

```bash
# Credit Bureau APIs
EXPERIAN_API_KEY=your-production-key
EQUIFAX_API_KEY=your-production-key
TRANSUNION_API_KEY=your-production-key

# Watchlist APIs
OFAC_API_KEY=your-production-key
EU_SANCTIONS_API_KEY=your-production-key
UN_SANCTIONS_API_KEY=your-production-key

# Social Media APIs
FACEBOOK_APP_ID=your-app-id
TWITTER_BEARER_TOKEN=your-token
LINKEDIN_CLIENT_ID=your-client-id

# And many more... (see .env.example)
```

## 📊 Monitoring and Observability

### Built-in Monitoring
- **Real-time Status**: Service health and performance metrics
- **Log Aggregation**: Centralized logging for all services
- **Error Tracking**: Automatic error detection and reporting
- **Resource Monitoring**: CPU, memory, disk, and network usage

### Optional Advanced Monitoring
If Prometheus and Grafana are enabled:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)

### Metrics Available
- Request counts and success rates
- Processing times and throughput
- System resource utilization
- Service health and availability
- Error rates and types

## 🚀 Production Deployment

### Prerequisites
1. **Docker & Docker Compose** - For infrastructure services
2. **Python 3.8+** - For agent services
3. **Rust & Cargo** - For core orchestrator
4. **Sufficient Resources** - 4GB RAM minimum, 8GB recommended

### Deployment Steps
1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd ComplianceAI
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

3. **Start Services**
   ```bash
   ./start-kyc-simple.sh
   ```

4. **Verify Deployment**
   ```bash
   ./check-kyc-status-simple.sh full
   ```

### Production Checklist
- [ ] Real API keys configured
- [ ] Authentication enabled (`REQUIRE_AUTH=true`)
- [ ] SSL/TLS certificates configured
- [ ] Firewall rules configured
- [ ] Backup and recovery procedures in place
- [ ] Monitoring and alerting configured
- [ ] Log rotation configured
- [ ] Resource limits set appropriately

## 📞 Support and Maintenance

### Getting Help
1. **Check Status**: `./check-kyc-status-simple.sh full`
2. **View Logs**: Check `logs/` directory
3. **User Guide**: http://localhost:8000/userguide (when running)
4. **Health Checks**: Use `/health` endpoints

### Regular Maintenance
- **Log Rotation**: Implement log rotation for production
- **Updates**: Regular security and dependency updates
- **Backups**: Regular database and configuration backups
- **Monitoring**: Continuous monitoring of system health

### Script Updates
All scripts support `--help` for detailed usage:
```bash
./start-kyc-simple.sh --help
./stop-kyc-platform.sh help
./check-kyc-status-simple.sh help
```

---

## 🎯 Quick Reference

### Essential Commands
```bash
# Start everything
./start-kyc-simple.sh

# Check status
./check-kyc-status-simple.sh

# Stop everything
./stop-kyc-platform.sh

# Force stop
./stop-kyc-platform.sh force

# Detailed status
./check-kyc-status-simple.sh full

# Check prerequisites only
./start-kyc-simple.sh --check-only
```

### Service URLs (when running)
- **Main Platform**: http://localhost:8000
- **User Guide**: http://localhost:8000/userguide
- **API Documentation**: http://localhost:8000/api/stats
- **Health Check**: http://localhost:8000/health

The KYC Automation Platform is now ready for comprehensive testing and deployment! 🚀
