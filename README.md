# KYC Automation Platform

A comprehensive, AI-powered Know Your Customer (KYC) automation platform built with Rust and Python, designed for financial institutions and compliance-heavy industries.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB+ RAM recommended
- 10GB+ free disk space

### Launch the Platform
```bash
# Clone the repository
git clone <repository-url>
cd ComplianceAI

# Start all services
docker-compose up --build

# Access the platform
open http://localhost:8000
```

## 🏗️ Architecture Overview

The platform uses a microservices architecture with the following components:

### Core Services
- **Rust Core**: Main orchestration service with web UI
- **OCR Agent**: Document text extraction (Python/FastAPI)
- **Face Agent**: Biometric verification (Python/FastAPI)
- **Watchlist Agent**: AML compliance screening (Python/FastAPI)
- **Data Integration Agent**: External data enrichment (Python/FastAPI)
- **QA Agent**: Quality assurance validation (Python/FastAPI)

### Infrastructure Services
- **Apache Kafka**: Message queuing and workflow coordination
- **Pinecone**: Vector database for similarity search
- **PostgreSQL**: Persistent data storage (optional)
- **Redis**: Caching layer (optional)
- **Nginx**: Reverse proxy (production)

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
# Edit .env with your specific settings
```

### Client Overrides
Customize settings in `configs/client_override.yaml`:

```yaml
# Example: Override agent endpoints
agents:
  ocr_agent: "http://custom-ocr-service:8001"
  
# Example: Enable authentication
auth:
  require_auth: true
  jwt_secret: "your-production-secret"
```

## 📊 Features

### ✅ Document Processing
- **OCR Extraction**: Tesseract-based text extraction
- **Quality Assessment**: Document quality scoring
- **Multi-format Support**: JPG, PNG, PDF, TIFF
- **Structured Data**: Name, DOB, ID number extraction

### ✅ Biometric Verification
- **Face Recognition**: Photo-to-ID matching
- **Liveness Detection**: Anti-spoofing measures
- **Quality Scoring**: Face image quality assessment
- **Multiple Algorithms**: Configurable detection methods

### ✅ Compliance Screening
- **Watchlist Matching**: OFAC, EU, UN sanctions
- **PEP Screening**: Politically Exposed Persons
- **Fuzzy Matching**: Configurable similarity thresholds
- **Risk Scoring**: Automated risk assessment

### ✅ Data Integration
- **Email Verification**: Deliverability and reputation
- **Phone Validation**: Carrier and location lookup
- **Credit Bureau**: Credit score and history (mock)
- **Social Media**: Profile verification and analysis
- **Address Verification**: Deliverability and geocoding

### ✅ Quality Assurance
- **Cross-validation**: Data consistency checks
- **Policy Compliance**: Automated rule validation
- **Exception Handling**: Comprehensive error reporting
- **Confidence Scoring**: Overall quality assessment

## 🎯 Usage

### Web Interface
1. Navigate to `http://localhost:8000`
2. Upload ID document and selfie
3. Configure processing options
4. Submit for verification
5. View comprehensive results

### API Integration
```bash
# Submit KYC request
curl -X POST http://localhost:8000/submit \
  -F "file_id=@id_document.jpg" \
  -F "file_selfie=@selfie.jpg" \
  -F "customer_email=customer@example.com"

# Check results
curl http://localhost:8000/result/{request_id}
```

## 🔒 Security & Compliance

### Data Protection
- **Encryption**: AES-256-GCM for data at rest
- **TLS**: All communications encrypted in transit
- **Access Control**: Role-based permissions
- **Audit Trail**: Comprehensive logging

### Compliance Standards
- **GDPR**: EU data protection compliance
- **PCI-DSS**: Payment card industry standards
- **SOC 2**: Security and availability controls
- **ISO 27001**: Information security management

### Data Retention
- **Documents**: 7 years (configurable)
- **Results**: 7 years (configurable)
- **Audit Logs**: 3 years (configurable)
- **Automatic Cleanup**: Scheduled data purging

## 📈 Monitoring & Operations

### Health Checks
```bash
# Check all services
curl http://localhost:8000/health

# Individual service health
curl http://localhost:8001/health  # OCR Agent
curl http://localhost:8002/health  # Face Agent
curl http://localhost:8003/health  # Watchlist Agent
```

### Metrics & Monitoring
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **ELK Stack**: Log aggregation and analysis
- **Custom Metrics**: Processing times, success rates

### Performance Tuning
```yaml
# docker-compose.yml resource limits
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
```

## 🧪 Testing

### Automated Testing
```bash
# Run all tests
docker-compose -f docker-compose.test.yml up --build

# Individual service tests
cd python-agents/ocr-agent
python -m pytest tests/

cd rust-core
cargo test
```

### Load Testing
```bash
# Install k6
brew install k6  # macOS
# or download from https://k6.io

# Run load tests
k6 run tests/load/kyc-workflow.js
```

## 🔧 Development

### Local Development
```bash
# Start infrastructure services only
docker-compose up kafka pinecone-emulator

# Run Rust core locally
cd rust-core
cargo run

# Run Python agents locally
cd python-agents/ocr-agent
pip install -r requirements.txt
python ocr_service.py
```

### Adding Custom Agents
1. Create new agent directory in `python-agents/`
2. Implement FastAPI service with `/process` endpoint
3. Add Dockerfile and requirements.txt
4. Update docker-compose.yml
5. Configure endpoint in `configs/default.yaml`

### Code Quality
```bash
# Rust formatting and linting
cargo fmt
cargo clippy

# Python formatting and linting
black python-agents/
flake8 python-agents/
```

## 🚀 Deployment

### Production Deployment
```bash
# Production configuration
export COMPOSE_PROFILES=production,monitoring,database

# Deploy with production settings
docker-compose up -d

# Enable SSL/TLS
# Configure nginx/ssl/ directory with certificates
```

### Scaling
```bash
# Scale specific services
docker-compose up -d --scale ocr-agent=3 --scale face-agent=2

# Kubernetes deployment (advanced)
kubectl apply -f k8s/
```

### Backup & Recovery
```bash
# Database backup
docker-compose exec postgres pg_dump -U kyc_user kyc_platform > backup.sql

# Volume backup
docker run --rm -v kyc_shared-uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads.tar.gz /data
```

## 📚 Documentation

### API Documentation
- **Swagger UI**: `http://localhost:8000/docs` (when available)
- **OpenAPI Spec**: Available in `docs/api/` directory
- **Postman Collection**: `docs/postman/KYC-Platform.json`

### User Guides
- **Web Interface**: `http://localhost:8000/userguide`
- **Administrator Guide**: `docs/admin-guide.md`
- **Developer Guide**: `docs/developer-guide.md`
- **Troubleshooting**: `docs/troubleshooting.md`

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Code Standards
- **Rust**: Follow `rustfmt` and `clippy` recommendations
- **Python**: Follow PEP 8, use `black` for formatting
- **Documentation**: Update relevant docs with changes
- **Testing**: Add tests for new functionality

## 🐛 Troubleshooting

### Common Issues

#### Port Conflicts
The platform automatically resolves port conflicts, but you can manually configure:
```yaml
# docker-compose.override.yml
services:
  rust-core:
    ports:
      - "8080:8000"  # Use port 8080 instead of 8000
```

#### Memory Issues
```bash
# Increase Docker memory limit
# Docker Desktop: Settings > Resources > Memory > 8GB+

# Reduce service resource usage
docker-compose -f docker-compose.lite.yml up
```

#### Service Startup Failures
```bash
# Check service logs
docker-compose logs rust-core
docker-compose logs ocr-agent

# Restart specific service
docker-compose restart ocr-agent
```

### Getting Help
- **Issues**: Create GitHub issue with logs and configuration
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check `docs/` directory for detailed guides

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Tesseract OCR**: Google's OCR engine
- **face_recognition**: Adam Geitgey's face recognition library
- **Actix Web**: Rust web framework
- **FastAPI**: Modern Python web framework
- **Apache Kafka**: Distributed streaming platform
- **Pinecone**: Vector database platform

---

**Version**: 1.0.0  
**Last Updated**: December 2024  
**Minimum Docker Version**: 20.10+  
**Minimum Docker Compose Version**: 2.0+
