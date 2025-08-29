#!/bin/bash

# KYC Automation Platform - Simple Startup Script
# Compatible with older bash versions (macOS default)
# This script starts all backend services, frontend, and UI components

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

# Utility functions
print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        KYC Automation Platform                               ║"
    echo "║                      Simple Startup Script                                  ║"
    echo "║                                                                              ║"
    echo "║  This script will start all services including:                             ║"
    echo "║  • Infrastructure (Kafka, Zookeeper)                                       ║"
    echo "║  • Python Agents (OCR, Face, Watchlist, Data Integration, QA)              ║"
    echo "║  • Rust Core (Orchestrator + Web UI)                                       ║"
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
        if docker-compose ps | grep -q "Up.*zookeeper" && \
           docker-compose ps | grep -q "Up.*kafka"; then
            log "Infrastructure services are running ✓"
            break
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

# Start Python agent
start_python_agent() {
    local agent_name=$1
    local port=$2
    local agent_dir="$SCRIPT_DIR/python-agents/$agent_name"
    
    if [ ! -d "$agent_dir" ]; then
        error "Agent directory not found: $agent_dir"
        return 1
    fi
    
    info "Starting $agent_name on port $port..."
    
    cd "$agent_dir"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log "Created virtual environment for $agent_name"
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt > "$LOG_DIR/agents/${agent_name}-install.log" 2>&1
    fi
    
    # Start the agent service
    export PORT=$port
    export PYTHONPATH="$agent_dir"
    
    local service_file=""
    case $agent_name in
        "ocr-agent")
            service_file="ocr_service.py"
            ;;
        "face-agent")
            service_file="face_service.py"
            ;;
        "watchlist-agent")
            service_file="watchlist_service.py"
            ;;
        "data-integration-agent")
            service_file="data_integration_service.py"
            ;;
        "quality-assurance-agent")
            service_file="qa_service.py"
            ;;
    esac
    
    if [ -f "$service_file" ]; then
        nohup python3 "$service_file" \
            > "$LOG_DIR/agents/${agent_name}.log" 2>&1 &
        local pid=$!
        echo $pid > "$PID_DIR/${agent_name}.pid"
        
        # Wait for service to start
        sleep 5
        if kill -0 $pid 2>/dev/null; then
            log "$agent_name started successfully (PID: $pid) ✓"
        else
            error "$agent_name failed to start"
            return 1
        fi
    else
        error "Service file not found: $service_file"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
}

# Start all Python agents
start_python_agents() {
    log "Starting Python agents..."
    
    start_python_agent "ocr-agent" $OCR_AGENT_PORT
    start_python_agent "face-agent" $FACE_AGENT_PORT
    start_python_agent "watchlist-agent" $WATCHLIST_AGENT_PORT
    start_python_agent "data-integration-agent" $DATA_INTEGRATION_PORT
    start_python_agent "quality-assurance-agent" $QA_AGENT_PORT
}

# Start Rust core service
start_rust_core() {
    log "Starting Rust core service..."
    
    cd "$SCRIPT_DIR/rust-core"
    
    # Build the Rust application
    info "Building Rust application..."
    cargo build --release > "$LOG_DIR/core/build.log" 2>&1
    
    if [ $? -ne 0 ]; then
        error "Failed to build Rust application"
        return 1
    fi
    
    # Set environment variables for Rust core
    export RUST_LOG=info
    export PORT=$RUST_CORE_PORT
    export OCR_AGENT_URL="http://localhost:$OCR_AGENT_PORT"
    export FACE_AGENT_URL="http://localhost:$FACE_AGENT_PORT"
    export WATCHLIST_AGENT_URL="http://localhost:$WATCHLIST_AGENT_PORT"
    export DATA_INTEGRATION_AGENT_URL="http://localhost:$DATA_INTEGRATION_PORT"
    export QA_AGENT_URL="http://localhost:$QA_AGENT_PORT"
    
    # Start the Rust core service
    nohup ./target/release/kyc-platform \
        > "$LOG_DIR/core/rust-core.log" 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/rust-core.pid"
    
    # Wait for service to start
    sleep 10
    if kill -0 $pid 2>/dev/null; then
        log "Rust core service started successfully (PID: $pid) ✓"
    else
        error "Rust core service failed to start"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
}

# Display service status
show_service_status() {
    echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗"
    echo -e "║                            SERVICE STATUS                                    ║"
    echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n"
    
    printf "%-25s %-10s %-30s\n" "Service" "Status" "URL"
    printf "%-25s %-10s %-30s\n" "-------" "------" "---"
    
    # Check each service
    local services=(
        "rust-core:$RUST_CORE_PORT"
        "ocr-agent:$OCR_AGENT_PORT"
        "face-agent:$FACE_AGENT_PORT"
        "watchlist-agent:$WATCHLIST_AGENT_PORT"
        "data-integration-agent:$DATA_INTEGRATION_PORT"
        "qa-agent:$QA_AGENT_PORT"
    )
    
    for service_info in "${services[@]}"; do
        local service_name="${service_info%:*}"
        local port="${service_info#*:}"
        local url="http://localhost:$port"
        
        if check_port $port; then
            printf "%-25s ${GREEN}%-10s${NC} %-30s\n" "$service_name" "✓ Running" "$url"
        else
            printf "%-25s ${RED}%-10s${NC} %-30s\n" "$service_name" "✗ Stopped" "N/A"
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
    
    # Stop services using PID files
    if [ -d "$PID_DIR" ]; then
        for pid_file in "$PID_DIR"/*.pid; do
            if [ -f "$pid_file" ]; then
                local pid=$(cat "$pid_file")
                local service=$(basename "$pid_file" .pid)
                if kill -0 $pid 2>/dev/null; then
                    log "Stopping $service (PID: $pid)..."
                    kill $pid
                fi
                rm -f "$pid_file"
            fi
        done
    fi
    
    # Stop Docker services
    if command -v docker-compose &> /dev/null; then
        log "Stopping Docker services..."
        docker-compose down > /dev/null 2>&1
    fi
    
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
    
    # Display status and access information
    show_service_status
    show_access_info
    
    log "KYC Automation Platform started successfully! 🚀"
    
    # Keep script running
    echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"
    
    # Monitor services
    while true; do
        sleep 30
        
        # Simple health check - just check if PID files exist and processes are running
        local failed_services=()
        if [ -d "$PID_DIR" ]; then
            for pid_file in "$PID_DIR"/*.pid; do
                if [ -f "$pid_file" ]; then
                    local pid=$(cat "$pid_file")
                    local service=$(basename "$pid_file" .pid)
                    if ! kill -0 $pid 2>/dev/null; then
                        failed_services+=("$service")
                    fi
                fi
            done
        fi
        
        if [ ${#failed_services[@]} -gt 0 ]; then
            warn "Detected failed services: ${failed_services[*]}"
        fi
    done
}

# Help function
show_help() {
    echo "KYC Automation Platform Simple Startup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --check-only   Only check prerequisites and port availability"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
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
