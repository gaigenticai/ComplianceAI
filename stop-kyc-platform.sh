#!/usr/bin/env bash

# KYC Automation Platform - Stop Script
# This script gracefully stops all services started by start-kyc-platform.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/pids"

# Utility functions
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
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

print_banner() {
    echo -e "${RED}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        KYC Automation Platform                               ║"
    echo "║                            Stop Script                                      ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Stop service by PID
stop_service_by_pid() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping $service_name (PID: $pid)..."
            kill "$pid"
            
            # Wait for graceful shutdown
            local wait_time=0
            while kill -0 "$pid" 2>/dev/null && [ $wait_time -lt 10 ]; do
                sleep 1
                ((wait_time++))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                warn "Force killing $service_name (PID: $pid)"
                kill -9 "$pid"
            fi
            
            log "$service_name stopped ✓"
        else
            warn "$service_name was not running (stale PID file)"
        fi
        
        rm -f "$pid_file"
    else
        info "No PID file found for $service_name"
    fi
}

# Stop all Python agents
stop_python_agents() {
    log "Stopping Python agents..."
    
    local agents=("ocr-agent" "face-agent" "watchlist-agent" "data-integration-agent" "quality-assurance-agent")
    
    for agent in "${agents[@]}"; do
        stop_service_by_pid "$agent"
    done
}

# Stop Rust core service
stop_rust_core() {
    log "Stopping Rust core service..."
    stop_service_by_pid "rust-core"
}

# Stop Docker services
stop_docker_services() {
    log "Stopping Docker services..."
    
    if command -v docker-compose &> /dev/null; then
        if docker-compose ps | grep -q "Up"; then
            info "Found running Docker services, stopping..."
            docker-compose down --remove-orphans
            log "Docker services stopped ✓"
        else
            info "No running Docker services found"
        fi
    else
        warn "Docker Compose not available"
    fi
}

# Kill processes by port (fallback method)
kill_by_port() {
    local port=$1
    local service_name=$2
    
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        log "Killing process on port $port ($service_name)..."
        kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null
        log "Process on port $port killed ✓"
    fi
}

# Comprehensive cleanup
comprehensive_cleanup() {
    log "Performing comprehensive cleanup..."
    
    # Common ports used by the platform
    local ports=(8000 8001 8002 8003 8004 8005 9092 2181 8080 9090 3000)
    local service_names=("rust-core" "ocr-agent" "face-agent" "watchlist-agent" "data-integration-agent" "qa-agent" "kafka" "zookeeper" "pinecone" "prometheus" "grafana")
    
    for i in "${!ports[@]}"; do
        kill_by_port "${ports[$i]}" "${service_names[$i]}"
    done
    
    # Clean up any remaining Python processes
    pkill -f "python.*_service.py" 2>/dev/null || true
    pkill -f "kyc-platform" 2>/dev/null || true
    
    # Clean up PID directory
    if [ -d "$PID_DIR" ]; then
        rm -f "$PID_DIR"/*.pid
        log "Cleaned up PID files ✓"
    fi
}

# Show running services
show_running_services() {
    echo -e "\n${BLUE}Checking for running KYC services...${NC}\n"
    
    local found_services=false
    local ports=(8000 8001 8002 8003 8004 8005 9092 2181 8080 9090 3000)
    local service_names=("Rust Core" "OCR Agent" "Face Agent" "Watchlist Agent" "Data Integration" "QA Agent" "Kafka" "Zookeeper" "Pinecone" "Prometheus" "Grafana")
    
    for i in "${!ports[@]}"; do
        local port="${ports[$i]}"
        local service="${service_names[$i]}"
        local pid=$(lsof -ti:$port 2>/dev/null)
        
        if [ -n "$pid" ]; then
            echo -e "${YELLOW}  $service running on port $port (PID: $pid)${NC}"
            found_services=true
        fi
    done
    
    if [ "$found_services" = false ]; then
        echo -e "${GREEN}  No KYC services currently running${NC}"
    fi
    
    echo ""
}

# Main execution
main() {
    print_banner
    
    case "${1:-stop}" in
        "stop")
            log "Stopping KYC Automation Platform..."
            
            stop_rust_core
            stop_python_agents
            stop_docker_services
            
            log "All services stopped successfully! ✓"
            ;;
            
        "force")
            warn "Force stopping all services..."
            comprehensive_cleanup
            log "Force stop completed! ✓"
            ;;
            
        "status")
            show_running_services
            ;;
            
        "help"|"-h"|"--help")
            echo "KYC Automation Platform Stop Script"
            echo ""
            echo "Usage: $0 [COMMAND]"
            echo ""
            echo "Commands:"
            echo "  stop     Gracefully stop all services (default)"
            echo "  force    Force kill all services and cleanup"
            echo "  status   Show running services"
            echo "  help     Show this help message"
            echo ""
            ;;
            
        *)
            error "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
