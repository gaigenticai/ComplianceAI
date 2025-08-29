# KYC Automation Platform - Startup Guide

This guide provides comprehensive instructions for starting, managing, and testing the KYC Automation Platform using the provided shell scripts.

## 🚀 Quick Start

### Prerequisites

Before running the platform, ensure you have the following installed:

- **Docker & Docker Compose** (for infrastructure services)
- **Python 3.8+** (for agent services)
- **Rust & Cargo** (for core orchestrator)
- **curl** (for health checks)
- **lsof** (for port management)

### 1. Start the Platform

```bash
./start-kyc-platform.sh
```

This single command will:
- ✅ Check all prerequisites
- ✅ Set up environment variables
- ✅ Resolve port conflicts automatically
- ✅ Start infrastructure services (Kafka, Zookeeper, Pinecone)
- ✅ Start all Python agents (OCR, Face, Watchlist, Data Integration, QA)
- ✅ Start Rust core service (Main UI + API)
- ✅ Start monitoring services (Prometheus, Grafana)
- ✅ Display access URLs and status

### 2. Access the Platform

Once started, access the platform at:

- **🌐 Main KYC Interface**: http://localhost:8000
- **📖 User Guide**: http://localhost:8000/userguide
- **📊 API Statistics**: http://localhost:8000/api/stats
- **❤️ Health Check**: http://localhost:8000/health

### 3. Stop the Platform

```bash
./stop-kyc-platform.sh
```

Or for force stop:
```bash
./stop-kyc-platform.sh force
```

## 📋 Available Scripts

### 1. `start-kyc-platform.sh` - Main Startup Script

**Usage:**
```bash
./start-kyc-platform.sh [OPTIONS]
```

**Options:**
- `--help` - Show help message
- `--no-monitoring` - Skip Prometheus/Grafana
- `--dev-mode` - Enable debug logging
- `--check-only` - Only check prerequisites

**Features:**
- 🔧 Automatic port conflict resolution
- 🏥 Health checks for all services
- 📝 Comprehensive logging
- 🔄 Service monitoring and restart detection
- 🎨 Colored output with progress indicators
- 🛡️ Graceful error handling and cleanup

### 2. `stop-kyc-platform.sh` - Stop Script

**Usage:**
```bash
./stop-kyc-platform.sh [COMMAND]
```

**Commands:**
- `stop` - Graceful shutdown (default)
- `force` - Force kill all services
- `status` - Show running services
- `help` - Show help message

### 3. `check-kyc-status.sh` - Status Monitor

**Usage:**
```bash
./check-kyc-status.sh [COMMAND]
```

**Commands:**
- `status` - Basic service status (default)
- `full` - Detailed status with system resources
- `logs` - Show log information
- `resources` - System resource usage
- `urls` - Quick access URLs

## 🏗️ Architecture Overview

The platform consists of several components:

### Infrastructure Services
- **Kafka** (Port 9092) - Message broker
- **Zookeeper** (Port 2181) - Kafka coordination
- **Pinecone** (Port 8080) - Vector database

### Python Agent Services
- **OCR Agent** (Port 8001) - Document text extraction
- **Face Agent** (Port 8002) - Facial recognition & liveness
- **Watchlist Agent** (Port 8003) - Sanctions screening
- **Data Integration** (Port 8004) - External API integration
- **QA Agent** (Port 8005) - Quality assurance

### Core Services
- **Rust Core** (Port 8000) - Main orchestrator + Web UI

### Monitoring (Optional)
- **Prometheus** (Port 9090) - Metrics collection
- **Grafana** (Port 3000) - Dashboards

## 🧪 Testing the Platform

### 1. Web Interface Testing

1. Open http://localhost:8000 in your browser
2. Upload test documents (ID, passport, etc.)
3. Fill in customer information
4. Submit for KYC processing
5. View results and processing details

### 2. API Testing

```bash
# Health check
curl http://localhost:8000/health

# System statistics
curl http://localhost:8000/api/stats

# Individual agent health
curl http://localhost:8001/health  # OCR Agent
curl http://localhost:8002/health  # Face Agent
curl http://localhost:8003/health  # Watchlist Agent
curl http://localhost:8004/health  # Data Integration
curl http://localhost:8005/health  # QA Agent
```

### 3. User Guide

The platform includes a comprehensive web-based user guide:
- **URL**: http://localhost:8000/userguide
- **Features**: Step-by-step instructions, API documentation, troubleshooting

## 📁 Directory Structure

```
ComplianceAI/
├── start-kyc-platform.sh      # Main startup script
├── stop-kyc-platform.sh       # Stop script
├── check-kyc-status.sh        # Status monitoring
├── logs/                       # Service logs
│   ├── infrastructure/         # Docker service logs
│   ├── agents/                 # Python agent logs
│   ├── core/                   # Rust core logs
│   └── monitoring/             # Monitoring logs
├── pids/                       # Process ID files
├── .env                        # Environment variables
└── .env.example               # Environment template
```

## 🔧 Configuration

### Environment Variables

The platform uses environment variables for configuration. Key variables:

```bash
# Core Configuration
REQUIRE_AUTH=false              # Enable/disable authentication
RUST_LOG=info                   # Log level
SERVER_HOST=0.0.0.0            # Server bind address
SERVER_PORT=8000               # Main server port

# External API Keys (required for production)
OFAC_API_KEY=your-key-here
EU_SANCTIONS_API_KEY=your-key-here
EXPERIAN_API_KEY=your-key-here
# ... (see .env.example for complete list)
```

### Port Configuration

The startup script automatically resolves port conflicts. Default ports:

- Rust Core: 8000
- OCR Agent: 8001
- Face Agent: 8002
- Watchlist Agent: 8003
- Data Integration: 8004
- QA Agent: 8005

## 🐛 Troubleshooting

### Common Issues

1. **Port Conflicts**
   - The script automatically resolves conflicts
   - Check `./check-kyc-status.sh` for actual ports used

2. **Docker Services Won't Start**
   ```bash
   # Check Docker status
   docker info
   
   # Restart Docker services
   docker-compose down
   docker-compose up -d
   ```

3. **Python Dependencies**
   ```bash
   # Each agent creates its own virtual environment
   # If issues occur, delete venv folders and restart
   rm -rf python-agents/*/venv
   ./start-kyc-platform.sh
   ```

4. **Rust Build Issues**
   ```bash
   # Clean and rebuild
   cd rust-core
   cargo clean
   cargo build --release
   ```

### Log Analysis

```bash
# View recent logs
./check-kyc-status.sh logs

# View specific service logs
tail -f logs/core/rust-core.log
tail -f logs/agents/ocr-agent.log

# Check for errors
grep -r "ERROR\|FATAL" logs/
```

### Service Health

```bash
# Check all services
./check-kyc-status.sh full

# Check specific service
curl http://localhost:8000/health
```

## 🔒 Security Considerations

### Development vs Production

The scripts are configured for development by default:

- **Development**: `REQUIRE_AUTH=false`
- **Production**: Set `REQUIRE_AUTH=true` and configure JWT secrets

### API Keys

For production use, configure real API keys in `.env`:

```bash
# Credit Bureau APIs
EXPERIAN_API_KEY=your-production-key
EQUIFAX_API_KEY=your-production-key
TRANSUNION_API_KEY=your-production-key

# Watchlist APIs
OFAC_API_KEY=your-production-key
EU_SANCTIONS_API_KEY=your-production-key
UN_SANCTIONS_API_KEY=your-production-key

# And many more... (see .env.example)
```

## 📈 Monitoring & Observability

### Built-in Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)
- **API Stats**: http://localhost:8000/api/stats

### Metrics Available

- Request counts and success rates
- Processing times
- System resource usage
- Service health status
- Error rates and types

## 🆘 Support

### Getting Help

1. **Check Status**: `./check-kyc-status.sh full`
2. **View Logs**: Check `logs/` directory
3. **User Guide**: http://localhost:8000/userguide
4. **Health Checks**: Use `/health` endpoints

### Script Options

All scripts support `--help` for detailed usage information:

```bash
./start-kyc-platform.sh --help
./stop-kyc-platform.sh help
./check-kyc-status.sh help
```

---

## 🎯 Quick Commands Reference

```bash
# Start everything
./start-kyc-platform.sh

# Check status
./check-kyc-status.sh

# Stop everything
./stop-kyc-platform.sh

# Force stop
./stop-kyc-platform.sh force

# Development mode
./start-kyc-platform.sh --dev-mode

# Check prerequisites only
./start-kyc-platform.sh --check-only

# Detailed status
./check-kyc-status.sh full
```

The KYC Automation Platform is now ready for testing and development! 🚀
