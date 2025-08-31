#!/bin/bash

# Agentic AI KYC Engine - Production Deployment Script
# This script handles the complete deployment of the KYC system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    success "All prerequisites met"
}

# Setup environment
setup_environment() {
    log "Setting up environment..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            warning "Created .env from .env.example. Please review and update the configuration."
            echo ""
            echo "Key variables to configure:"
            echo "- OPENAI_API_KEY: Your OpenAI API key (required for AI agents)"
            echo "- JWT_SECRET: Change the default JWT secret"
            echo "- Database passwords: Update default passwords"
            echo ""
            read -p "Press Enter to continue after updating .env file..."
        else
            error ".env.example file not found. Cannot create environment configuration."
            exit 1
        fi
    else
        success "Environment file (.env) already exists"
    fi
}

# Check ports availability
check_ports() {
    log "Checking port availability..."
    
    ports=(8000 8001 8002 8003 8004 8005 9090 3000 9092 5432 27017 6379)
    occupied_ports=()
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            occupied_ports+=($port)
        fi
    done
    
    if [ ${#occupied_ports[@]} -gt 0 ]; then
        warning "The following ports are already in use: ${occupied_ports[*]}"
        warning "You may need to stop other services or modify port configuration in docker-compose.yml"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        success "All required ports are available"
    fi
}

# Build and start services
deploy_services() {
    log "Building and starting services..."
    
    # Pull base images
    log "Pulling base images..."
    docker-compose pull
    
    # Build custom images
    log "Building custom images..."
    docker-compose build --parallel
    
    # Start services
    log "Starting services..."
    docker-compose up -d
    
    success "Services started successfully"
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    # Wait for core services
    services=(
        "http://localhost:8000/health:KYC Orchestrator"
        "http://localhost:8001/health:Data Ingestion Agent"
        "http://localhost:8002/health:KYC Analysis Agent"
        "http://localhost:8003/health:Decision Making Agent"
        "http://localhost:8004/health:Compliance Monitoring Agent"
        "http://localhost:8005/health:Data Quality Agent"
    )
    
    max_attempts=60
    attempt=0
    
    for service in "${services[@]}"; do
        url=$(echo $service | cut -d: -f1-2)
        name=$(echo $service | cut -d: -f3)
        
        log "Waiting for $name..."
        
        while [ $attempt -lt $max_attempts ]; do
            if curl -s -f "$url" > /dev/null 2>&1; then
                success "$name is ready"
                break
            fi
            
            attempt=$((attempt + 1))
            if [ $attempt -eq $max_attempts ]; then
                error "$name failed to start within timeout"
                exit 1
            fi
            
            sleep 5
        done
        
        attempt=0
    done
    
    success "All services are ready"
}

# Run health checks
run_health_checks() {
    log "Running comprehensive health checks..."
    
    # Check system status
    if curl -s -f "http://localhost:8000/api/v1/system/status" > /dev/null; then
        success "System status check passed"
    else
        error "System status check failed"
        exit 1
    fi
    
    # Check agents status
    if curl -s -f "http://localhost:8000/api/v1/agents/status" > /dev/null; then
        success "Agents status check passed"
    else
        error "Agents status check failed"
        exit 1
    fi
    
    success "All health checks passed"
}

# Run tests
run_tests() {
    log "Running automated tests..."
    
    if [ -f "tests/test_runner.py" ]; then
        if python3 tests/test_runner.py; then
            success "All tests passed"
        else
            warning "Some tests failed. System is deployed but may have issues."
        fi
    else
        warning "Test runner not found. Skipping tests."
    fi
}

# Display deployment information
show_deployment_info() {
    echo ""
    echo "🎉 Deployment Complete!"
    echo "===================="
    echo ""
    echo "🌐 Web Interface:"
    echo "   Main Dashboard: http://localhost:8000"
    echo "   User Guide: http://localhost:8000/userguide"
    echo ""
    echo "📊 Monitoring:"
    echo "   Prometheus: http://localhost:9090"
    echo "   Grafana: http://localhost:3000 (admin/admin)"
    echo ""
    echo "🔧 API Endpoints:"
    echo "   Health Check: http://localhost:8000/health"
    echo "   System Status: http://localhost:8000/api/v1/system/status"
    echo "   Process KYC: POST http://localhost:8000/api/v1/kyc/process"
    echo ""
    echo "🤖 AI Agents:"
    echo "   Data Ingestion: http://localhost:8001/health"
    echo "   KYC Analysis: http://localhost:8002/health"
    echo "   Decision Making: http://localhost:8003/health"
    echo "   Compliance Monitoring: http://localhost:8004/health"
    echo "   Data Quality: http://localhost:8005/health"
    echo ""
    echo "📝 Logs:"
    echo "   View logs: docker-compose logs -f [service-name]"
    echo "   All logs: docker-compose logs -f"
    echo ""
    echo "🛑 Management:"
    echo "   Stop system: docker-compose down"
    echo "   Restart: docker-compose restart"
    echo "   Update: docker-compose pull && docker-compose up -d"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "   Check status: docker-compose ps"
    echo "   Service logs: docker-compose logs [service-name]"
    echo "   System health: curl http://localhost:8000/health"
    echo ""
}

# Cleanup function
cleanup() {
    if [ $? -ne 0 ]; then
        error "Deployment failed. Cleaning up..."
        docker-compose down
    fi
}

# Main deployment function
main() {
    echo "🚀 Agentic AI KYC Engine - Production Deployment"
    echo "================================================"
    echo ""
    
    # Change to project root directory (parent of scripts directory)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    cd "$PROJECT_ROOT"
    
    log "Working directory: $(pwd)"
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Run deployment steps
    check_prerequisites
    setup_environment
    check_ports
    deploy_services
    wait_for_services
    run_health_checks
    
    # Optional: Run tests
    read -p "Run automated tests? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_tests
    fi
    
    show_deployment_info
    
    success "Deployment completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    "stop")
        # Change to project root directory
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
        cd "$PROJECT_ROOT"
        
        log "Stopping all services..."
        docker-compose down
        success "All services stopped"
        ;;
    "restart")
        # Change to project root directory
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
        cd "$PROJECT_ROOT"
        
        log "Restarting all services..."
        docker-compose restart
        success "All services restarted"
        ;;
    "logs")
        # Change to project root directory
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
        cd "$PROJECT_ROOT"
        
        docker-compose logs -f "${2:-}"
        ;;
    "status")
        # Change to project root directory
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
        cd "$PROJECT_ROOT"
        
        docker-compose ps
        echo ""
        curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
        ;;
    "test")
        # Change to project root directory
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
        cd "$PROJECT_ROOT"
        
        run_tests
        ;;
    "clean")
        # Change to project root directory
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
        cd "$PROJECT_ROOT"
        
        log "Cleaning up all containers and volumes..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        success "Cleanup completed"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (no args)  - Deploy the complete system"
        echo "  stop       - Stop all services"
        echo "  restart    - Restart all services"
        echo "  logs [svc] - Show logs (optionally for specific service)"
        echo "  status     - Show system status"
        echo "  test       - Run automated tests"
        echo "  clean      - Clean up containers and volumes"
        echo "  help       - Show this help message"
        ;;
    "")
        main
        ;;
    *)
        error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
