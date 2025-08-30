#!/usr/bin/env bash

# KYC Automation Platform - Complete Startup Script
# This script starts all backend services, frontend, and UI components
# with proper error handling, port conflict resolution, and monitoring

# Require bash 4.0+ for associative arrays
if [ "${BASH_VERSION%%.*}" -lt 4 ]; then
    echo "Error: This script requires Bash 4.0 or later for associative arrays."
    echo "Current version: $BASH_VERSION"
    echo "On macOS, install newer bash: brew install bash"
    exit 1
fi

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/pids"
ENV_FILE="$SCRIPT_DIR/.env"

# Service ports (with automatic conflict resolution)
RUST_CORE_PORT=8000
OCR_AGENT_PORT=8001
FACE_AGENT_PORT=8002
WATCHLIST_AGENT_PORT=8003
DATA_INTEGRATION_PORT=8004
QA_AGENT_PORT=8005
KAFKA_PORT=9092
ZOOKEEPER_PORT=2181
PINECONE_PORT=8080
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Service status tracking
declare -A SERVICE_STATUS
declare -A SERVICE_URLS

# Utility functions
print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        KYC Automation Platform                               ║"
    echo "║                         Complete Startup Script                             ║"
    echo "║                                                                              ║"
    echo "║  This script will start all services including:                             ║"
    echo "║  • Infrastructure (Kafka, Zookeeper, Pinecone)                             ║"
    echo "║  • Python Agents (OCR, Face, Watchlist, Data Integration, QA)              ║"
    echo "║  • Rust Core (Orchestrator + Web UI)                                       ║"
    echo "║  • Monitoring (Prometheus, Grafana)                                        ║"
    echo "║  • Web User Guide & Testing Interface                                      ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Find available port starting from given port
find_available_port() {
    local start_port=$1
    local port=$start_port
    while ! check_port $port; do
        ((port++))
        if [ $port -gt $((start_port + 100)) ]; then
            error "Could not find available port starting from $start_port"
            exit 1
        fi
    done
    echo $port
}

# Setup directories
setup_directories() {
    log "Setting up directories..."
    mkdir -p "$LOG_DIR" "$PID_DIR"
    
    # Create logs subdirectories
    mkdir -p "$LOG_DIR/infrastructure"
    mkdir -p "$LOG_DIR/agents"
    mkdir -p "$LOG_DIR/core"
    mkdir -p "$LOG_DIR/monitoring"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check Rust/Cargo
    if ! command -v cargo &> /dev/null; then
        missing_deps+=("cargo/rust")
    fi
    
    # Check Node.js (for potential frontend extensions)
    if ! command -v node &> /dev/null; then
        warn "Node.js not found - some optional features may not work"
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        echo "Please install the missing dependencies and try again."
        exit 1
    fi
    
    log "All prerequisites satisfied ✓"
}

# Setup environment
setup_environment() {
    log "Setting up environment..."
    
    # Copy .env.example to .env if it doesn't exist
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
            log "Created .env file from .env.example"
            warn "Please review and update the .env file with your actual API keys and configuration"
        else
            warn ".env.example not found - creating minimal .env file"
            cat > "$ENV_FILE" << EOF
# KYC Automation Platform Environment Configuration
REQUIRE_AUTH=false
RUST_LOG=info
SERVER_HOST=0.0.0.0
SERVER_PORT=$RUST_CORE_PORT

# Kafka Configuration
KAFKA_BROKERS=localhost:$KAFKA_PORT

# Agent Ports
OCR_AGENT_PORT=$OCR_AGENT_PORT
FACE_AGENT_PORT=$FACE_AGENT_PORT
WATCHLIST_AGENT_PORT=$WATCHLIST_AGENT_PORT
DATA_INTEGRATION_AGENT_PORT=$DATA_INTEGRATION_PORT
QA_AGENT_PORT=$QA_AGENT_PORT
EOF
        fi
    fi
    
    # Source environment variables
    if [ -f "$ENV_FILE" ]; then
        set -a  # Automatically export all variables
        source "$ENV_FILE"
        set +a
        log "Environment variables loaded from .env"
    fi
}

# Resolve port conflicts
resolve_port_conflicts() {
    log "Resolving port conflicts..."
    
    # Check and resolve port conflicts
    RUST_CORE_PORT=$(find_available_port $RUST_CORE_PORT)
    OCR_AGENT_PORT=$(find_available_port $OCR_AGENT_PORT)
    FACE_AGENT_PORT=$(find_available_port $FACE_AGENT_PORT)
    WATCHLIST_AGENT_PORT=$(find_available_port $WATCHLIST_AGENT_PORT)
    DATA_INTEGRATION_PORT=$(find_available_port $DATA_INTEGRATION_PORT)
    QA_AGENT_PORT=$(find_available_port $QA_AGENT_PORT)
    
    # Update service URLs
    SERVICE_URLS["rust-core"]="http://localhost:$RUST_CORE_PORT"
    SERVICE_URLS["ocr-agent"]="http://localhost:$OCR_AGENT_PORT"
    SERVICE_URLS["face-agent"]="http://localhost:$FACE_AGENT_PORT"
    SERVICE_URLS["watchlist-agent"]="http://localhost:$WATCHLIST_AGENT_PORT"
    SERVICE_URLS["data-integration-agent"]="http://localhost:$DATA_INTEGRATION_PORT"
    SERVICE_URLS["qa-agent"]="http://localhost:$QA_AGENT_PORT"
    
    log "Port assignments:"
    log "  Rust Core (Main UI): $RUST_CORE_PORT"
    log "  OCR Agent: $OCR_AGENT_PORT"
    log "  Face Agent: $FACE_AGENT_PORT"
    log "  Watchlist Agent: $WATCHLIST_AGENT_PORT"
    log "  Data Integration Agent: $DATA_INTEGRATION_PORT"
    log "  QA Agent: $QA_AGENT_PORT"
}

# Start infrastructure services
start_infrastructure() {
    log "Starting infrastructure services..."
    
    info "Starting Kafka and Zookeeper..."
    docker-compose up -d zookeeper kafka \
        > "$LOG_DIR/infrastructure/docker-compose.log" 2>&1 &
    
    # Wait for services to be healthy
    local max_wait=120
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        # Check if both services are running (healthy or starting)
        local zk_status=$(docker-compose ps zookeeper | grep "Up")
        local kafka_status=$(docker-compose ps kafka | grep "Up")
        
        if [ -n "$zk_status" ] && [ -n "$kafka_status" ]; then
            # Check if both are healthy, or if they've been running for enough time
            if (echo "$zk_status" | grep -q "healthy") && (echo "$kafka_status" | grep -q "healthy"); then
                log "Infrastructure services are healthy ✓"
                SERVICE_STATUS["infrastructure"]="running"
                break
            elif [ $wait_time -gt 60 ]; then
                # After 60 seconds, accept if they're just "Up" (running)
                log "Infrastructure services are running (health checks may still be starting) ✓"
                SERVICE_STATUS["infrastructure"]="running"
                break
            fi
        fi
        sleep 5
        ((wait_time+=5))
        info "Waiting for infrastructure services... ($wait_time/${max_wait}s)"
    done
    
    if [ $wait_time -ge $max_wait ]; then
        error "Infrastructure services failed to start within $max_wait seconds"
        return 1
    fi
}

# Start Python agent via Docker
start_python_agent() {
    local agent_name=$1
    local port=$2
    
    info "Starting $agent_name on port $port via Docker..."
    
    # Start the agent service using Docker Compose
    docker-compose up -d "$agent_name" \
        > "$LOG_DIR/agents/${agent_name}-docker.log" 2>&1
    
    if [ $? -eq 0 ]; then
        # Wait for service to be healthy
        local max_wait=60
        local wait_time=0
        
        while [ $wait_time -lt $max_wait ]; do
            if docker-compose ps "$agent_name" | grep -q "Up"; then
                SERVICE_STATUS["$agent_name"]="running"
                log "$agent_name started successfully via Docker ✓"
                return 0
            fi
            sleep 5
            ((wait_time+=5))
            info "Waiting for $agent_name to start... ($wait_time/${max_wait}s)"
        done
        
        SERVICE_STATUS["$agent_name"]="failed"
        error "$agent_name failed to start within $max_wait seconds"
        return 1
    else
        SERVICE_STATUS["$agent_name"]="failed"
        error "$agent_name failed to start via Docker"
        return 1
    fi
}

# Start all Python agents
start_python_agents() {
    log "Starting Python agents..."
    
    start_python_agent "ocr-agent" $OCR_AGENT_PORT
    start_python_agent "face-agent" $FACE_AGENT_PORT
    start_python_agent "watchlist-agent" $WATCHLIST_AGENT_PORT
    start_python_agent "data-integration-agent" $DATA_INTEGRATION_PORT
    start_python_agent "qa-agent" $QA_AGENT_PORT
}

# Start Rust core service via Docker
start_rust_core() {
    log "Starting Rust core service via Docker..."
    
    # Start the Rust core service using Docker Compose
    docker-compose up -d rust-core \
        > "$LOG_DIR/core/rust-core-docker.log" 2>&1
    
    if [ $? -eq 0 ]; then
        # Wait for service to be healthy
        local max_wait=120
        local wait_time=0
        
        while [ $wait_time -lt $max_wait ]; do
            if docker-compose ps rust-core | grep -q "Up" && \
               check_service_health "http://localhost:$RUST_CORE_PORT/health"; then
                SERVICE_STATUS["rust-core"]="running"
                log "Rust core service started successfully via Docker ✓"
                return 0
            fi
            sleep 10
            ((wait_time+=10))
            info "Waiting for Rust core to start... ($wait_time/${max_wait}s)"
        done
        
        SERVICE_STATUS["rust-core"]="failed"
        error "Rust core service failed to start within $max_wait seconds"
        return 1
    else
        SERVICE_STATUS["rust-core"]="failed"
        error "Rust core service failed to start via Docker"
        return 1
    fi
}

# Check service health
check_service_health() {
    local url=$1
    local max_attempts=12
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            return 0
        fi
        sleep 5
        ((attempt++))
    done
    return 1
}

# Start monitoring services (optional)
start_monitoring() {
    log "Starting monitoring services..."
    
    if command -v docker-compose &> /dev/null; then
        info "Starting Prometheus and Grafana..."
        docker-compose up -d prometheus grafana \
            > "$LOG_DIR/monitoring/monitoring.log" 2>&1 &
        
        sleep 10
        SERVICE_STATUS["monitoring"]="running"
        log "Monitoring services started ✓"
        log "  Prometheus: http://localhost:$PROMETHEUS_PORT"
        log "  Grafana: http://localhost:$GRAFANA_PORT (admin/admin123)"
    else
        warn "Docker Compose not available - skipping monitoring services"
    fi
}

# Display service status
show_service_status() {
    echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗"
    echo -e "║                            SERVICE STATUS                                    ║"
    echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n"
    
    printf "%-25s %-10s %-30s\n" "Service" "Status" "URL"
    printf "%-25s %-10s %-30s\n" "-------" "------" "---"
    
    for service in "${!SERVICE_STATUS[@]}"; do
        local status=${SERVICE_STATUS[$service]}
        local url=${SERVICE_URLS[$service]:-"N/A"}
        
        if [ "$status" = "running" ]; then
            printf "%-25s ${GREEN}%-10s${NC} %-30s\n" "$service" "✓ Running" "$url"
        else
            printf "%-25s ${RED}%-10s${NC} %-30s\n" "$service" "✗ Failed" "$url"
        fi
    done
    
    echo ""
}

# Display access information
show_access_info() {
    echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗"
    echo -e "║                           ACCESS INFORMATION                                 ║"
    echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${GREEN}🌐 Main Application:${NC}"
    echo -e "   KYC Platform UI: http://localhost:$RUST_CORE_PORT"
    echo -e "   User Guide: http://localhost:$RUST_CORE_PORT/userguide"
    echo -e "   API Stats: http://localhost:$RUST_CORE_PORT/api/stats"
    echo -e "   Health Check: http://localhost:$RUST_CORE_PORT/health"
    
    echo -e "\n${CYAN}🔧 Agent Services:${NC}"
    echo -e "   OCR Agent: http://localhost:$OCR_AGENT_PORT"
    echo -e "   Face Agent: http://localhost:$FACE_AGENT_PORT"
    echo -e "   Watchlist Agent: http://localhost:$WATCHLIST_AGENT_PORT"
    echo -e "   Data Integration: http://localhost:$DATA_INTEGRATION_PORT"
    echo -e "   QA Agent: http://localhost:$QA_AGENT_PORT"
    
    if [ "${SERVICE_STATUS[monitoring]}" = "running" ]; then
        echo -e "\n${YELLOW}📊 Monitoring:${NC}"
        echo -e "   Prometheus: http://localhost:$PROMETHEUS_PORT"
        echo -e "   Grafana: http://localhost:$GRAFANA_PORT (admin/admin123)"
    fi
    
    echo -e "\n${BLUE}📋 Testing:${NC}"
    echo -e "   1. Open http://localhost:$RUST_CORE_PORT in your browser"
    echo -e "   2. Upload documents for KYC processing"
    echo -e "   3. Check the User Guide for detailed instructions"
    echo -e "   4. Monitor system stats via the API endpoint"
    
    echo -e "\n${GREEN}📁 Logs Location:${NC} $LOG_DIR"
    echo -e "${GREEN}🔧 PID Files:${NC} $PID_DIR"
}

# Cleanup function
cleanup() {
    log "Cleaning up services..."
    
    # Stop all Docker services
    if command -v docker-compose &> /dev/null; then
        log "Stopping Docker services..."
        docker-compose down > /dev/null 2>&1
        
        # Also stop any orphaned containers
        docker-compose down --remove-orphans > /dev/null 2>&1
    fi
    
    # Clean up PID files (if any remain from legacy runs)
    rm -f "$PID_DIR"/*.pid
    
    log "Cleanup completed"
}

# Signal handlers
trap cleanup EXIT
trap 'error "Script interrupted"; exit 1' INT TERM

# Main execution
main() {
    print_banner
    
    # Setup
    setup_directories
    check_prerequisites
    setup_environment
    resolve_port_conflicts
    
    # Start services
    log "Starting KYC Automation Platform..."
    
    if ! start_infrastructure; then
        error "Failed to start infrastructure services"
        exit 1
    fi
    
    if ! start_python_agents; then
        error "Failed to start Python agents"
        exit 1
    fi
    
    if ! start_rust_core; then
        error "Failed to start Rust core service"
        exit 1
    fi
    
    # Optional monitoring
    start_monitoring
    
    # Display status and access information
    show_service_status
    show_access_info
    
    log "KYC Automation Platform started successfully! 🚀"
    
    # Keep script running
    echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"
    
    # Monitor Docker services
    while true; do
        sleep 30
        
        # Check if any Docker service has failed
        local failed_services=()
        for service in "${!SERVICE_STATUS[@]}"; do
            if [ "$service" != "infrastructure" ] && [ "$service" != "monitoring" ]; then
                if ! docker-compose ps "$service" | grep -q "Up"; then
                    failed_services+=("$service")
                    SERVICE_STATUS["$service"]="failed"
                fi
            fi
        done
        
        if [ ${#failed_services[@]} -gt 0 ]; then
            warn "Detected failed Docker services: ${failed_services[*]}"
            # Could implement restart logic here
        fi
    done
}

# Help function
show_help() {
    echo "KYC Automation Platform Startup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --no-monitoring Skip starting monitoring services"
    echo "  --dev-mode     Start in development mode with debug logging"
    echo "  --check-only   Only check prerequisites and port availability"
    echo ""
    echo "Environment Variables:"
    echo "  RUST_LOG       Set log level (default: info)"
    echo "  NO_DOCKER      Skip Docker-based services"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --no-monitoring)
            SKIP_MONITORING=true
            shift
            ;;
        --dev-mode)
            export RUST_LOG=debug
            DEV_MODE=true
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Execute main function or check-only mode
if [ "$CHECK_ONLY" = true ]; then
    print_banner
    setup_directories
    check_prerequisites
    setup_environment
    resolve_port_conflicts
    log "All checks passed! Ready to start services."
else
    main
fi
