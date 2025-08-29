#!/usr/bin/env bash

# KYC Automation Platform - Status Check Script
# This script provides detailed status information about all services

# Check for bash 4.0+ for associative arrays, fallback to simple arrays
if [ "${BASH_VERSION%%.*}" -ge 4 ]; then
    USE_ASSOC_ARRAYS=true
else
    USE_ASSOC_ARRAYS=false
    echo "Note: Using compatibility mode for older bash versions"
fi

set -e

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
PID_DIR="$SCRIPT_DIR/pids"
LOG_DIR="$SCRIPT_DIR/logs"

# Service configuration
declare -A SERVICE_PORTS=(
    ["rust-core"]=8000
    ["ocr-agent"]=8001
    ["face-agent"]=8002
    ["watchlist-agent"]=8003
    ["data-integration-agent"]=8004
    ["qa-agent"]=8005
    ["kafka"]=9092
    ["zookeeper"]=2181
    ["pinecone"]=8080
    ["prometheus"]=9090
    ["grafana"]=3000
)

declare -A SERVICE_NAMES=(
    ["rust-core"]="Rust Core (Main UI)"
    ["ocr-agent"]="OCR Agent"
    ["face-agent"]="Face Recognition Agent"
    ["watchlist-agent"]="Watchlist Screening Agent"
    ["data-integration-agent"]="Data Integration Agent"
    ["qa-agent"]="Quality Assurance Agent"
    ["kafka"]="Kafka Message Broker"
    ["zookeeper"]="Zookeeper"
    ["pinecone"]="Pinecone Vector DB"
    ["prometheus"]="Prometheus Monitoring"
    ["grafana"]="Grafana Dashboard"
)

# Utility functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

info() {
    echo -e "${CYAN}$1${NC}"
}

# Check if service is running on port
check_service_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Service is running
    else
        return 1  # Service is not running
    fi
}

# Check service health via HTTP
check_service_health() {
    local url=$1
    if curl -s -f "$url" > /dev/null 2>&1; then
        return 0  # Healthy
    else
        return 1  # Unhealthy
    fi
}

# Get process info for port
get_process_info() {
    local port=$1
    lsof -ti:$port 2>/dev/null | head -1
}

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        KYC Automation Platform                               ║"
    echo "║                           Status Check                                      ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Show detailed service status
show_service_status() {
    echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗"
    echo -e "║                            SERVICE STATUS                                    ║"
    echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n"
    
    printf "%-25s %-6s %-10s %-8s %-15s %-20s\n" "Service" "Port" "Status" "PID" "Health" "URL"
    printf "%-25s %-6s %-10s %-8s %-15s %-20s\n" "-------" "----" "------" "---" "------" "---"
    
    local total_services=0
    local running_services=0
    local healthy_services=0
    
    for service in "${!SERVICE_PORTS[@]}"; do
        local port=${SERVICE_PORTS[$service]}
        local name=${SERVICE_NAMES[$service]}
        local pid=""
        local status=""
        local health=""
        local url=""
        
        ((total_services++))
        
        if check_service_port $port; then
            pid=$(get_process_info $port)
            status="${GREEN}✓ Running${NC}"
            ((running_services++))
            
            # Check health for HTTP services
            case $service in
                "rust-core"|"ocr-agent"|"face-agent"|"watchlist-agent"|"data-integration-agent"|"qa-agent")
                    url="http://localhost:$port"
                    if check_service_health "$url/health" || check_service_health "$url"; then
                        health="${GREEN}✓ Healthy${NC}"
                        ((healthy_services++))
                    else
                        health="${YELLOW}⚠ Unhealthy${NC}"
                    fi
                    ;;
                "prometheus")
                    url="http://localhost:$port"
                    if check_service_health "$url"; then
                        health="${GREEN}✓ Healthy${NC}"
                        ((healthy_services++))
                    else
                        health="${YELLOW}⚠ Unhealthy${NC}"
                    fi
                    ;;
                "grafana")
                    url="http://localhost:$port"
                    if check_service_health "$url"; then
                        health="${GREEN}✓ Healthy${NC}"
                        ((healthy_services++))
                    else
                        health="${YELLOW}⚠ Unhealthy${NC}"
                    fi
                    ;;
                *)
                    health="${CYAN}N/A${NC}"
                    url="tcp://localhost:$port"
                    ;;
            esac
        else
            status="${RED}✗ Stopped${NC}"
            health="${RED}✗ Down${NC}"
            url="N/A"
        fi
        
        printf "%-25s %-6s %-10s %-8s %-15s %-20s\n" "$name" "$port" "$status" "$pid" "$health" "$url"
    done
    
    echo ""
    echo -e "${BLUE}Summary: $running_services/$total_services services running, $healthy_services healthy${NC}"
}

# Show system resources
show_system_resources() {
    echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗"
    echo -e "║                           SYSTEM RESOURCES                                   ║"
    echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n"
    
    # CPU usage
    if command -v top &> /dev/null; then
        local cpu_usage=$(top -l 1 -s 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
        echo -e "${CYAN}CPU Usage:${NC} ${cpu_usage}%"
    fi
    
    # Memory usage
    if command -v vm_stat &> /dev/null; then
        local mem_info=$(vm_stat | head -4)
        echo -e "${CYAN}Memory Info:${NC}"
        echo "$mem_info" | sed 's/^/  /'
    fi
    
    # Disk usage
    if command -v df &> /dev/null; then
        echo -e "${CYAN}Disk Usage:${NC}"
        df -h / | tail -1 | awk '{printf "  Root: %s used of %s (%s full)\n", $3, $2, $5}'
    fi
    
    # Docker status
    if command -v docker &> /dev/null; then
        echo -e "${CYAN}Docker Status:${NC}"
        if docker info > /dev/null 2>&1; then
            local containers=$(docker ps -q | wc -l | tr -d ' ')
            echo -e "  ${GREEN}✓ Docker running${NC} ($containers containers)"
        else
            echo -e "  ${RED}✗ Docker not running${NC}"
        fi
    fi
}

# Show log information
show_log_info() {
    echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗"
    echo -e "║                            LOG INFORMATION                                   ║"
    echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n"
    
    if [ -d "$LOG_DIR" ]; then
        echo -e "${CYAN}Log Directory:${NC} $LOG_DIR"
        echo -e "${CYAN}Recent Log Files:${NC}"
        
        find "$LOG_DIR" -name "*.log" -type f -mtime -1 | head -10 | while read -r logfile; do
            local size=$(du -h "$logfile" | cut -f1)
            local modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$logfile" 2>/dev/null || date -r "$logfile" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown")
            echo "  $(basename "$logfile") - $size - $modified"
        done
        
        # Show recent errors
        echo -e "\n${YELLOW}Recent Errors (last 10):${NC}"
        if find "$LOG_DIR" -name "*.log" -type f -exec grep -l "ERROR\|FATAL\|Exception" {} \; | head -5 | xargs grep -h "ERROR\|FATAL\|Exception" | tail -10 | grep -q .; then
            find "$LOG_DIR" -name "*.log" -type f -exec grep -l "ERROR\|FATAL\|Exception" {} \; | head -5 | xargs grep -h "ERROR\|FATAL\|Exception" | tail -10 | sed 's/^/  /'
        else
            echo "  No recent errors found"
        fi
    else
        echo -e "${YELLOW}Log directory not found: $LOG_DIR${NC}"
    fi
}

# Show quick access URLs
show_access_urls() {
    echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗"
    echo -e "║                            QUICK ACCESS                                      ║"
    echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n"
    
    local rust_port=${SERVICE_PORTS["rust-core"]}
    if check_service_port $rust_port; then
        echo -e "${GREEN}🌐 Main Application:${NC}"
        echo -e "   KYC Platform: http://localhost:$rust_port"
        echo -e "   User Guide: http://localhost:$rust_port/userguide"
        echo -e "   API Stats: http://localhost:$rust_port/api/stats"
        echo -e "   Health Check: http://localhost:$rust_port/health"
    else
        echo -e "${RED}Main application is not running${NC}"
    fi
    
    local prometheus_port=${SERVICE_PORTS["prometheus"]}
    local grafana_port=${SERVICE_PORTS["grafana"]}
    
    if check_service_port $prometheus_port || check_service_port $grafana_port; then
        echo -e "\n${CYAN}📊 Monitoring:${NC}"
        if check_service_port $prometheus_port; then
            echo -e "   Prometheus: http://localhost:$prometheus_port"
        fi
        if check_service_port $grafana_port; then
            echo -e "   Grafana: http://localhost:$grafana_port (admin/admin123)"
        fi
    fi
}

# Main execution
main() {
    print_banner
    
    case "${1:-status}" in
        "status"|"")
            show_service_status
            show_access_urls
            ;;
            
        "full"|"detailed")
            show_service_status
            show_system_resources
            show_log_info
            show_access_urls
            ;;
            
        "logs")
            show_log_info
            ;;
            
        "resources"|"system")
            show_system_resources
            ;;
            
        "urls"|"access")
            show_access_urls
            ;;
            
        "help"|"-h"|"--help")
            echo "KYC Automation Platform Status Check Script"
            echo ""
            echo "Usage: $0 [COMMAND]"
            echo ""
            echo "Commands:"
            echo "  status     Show service status (default)"
            echo "  full       Show detailed status including system resources and logs"
            echo "  logs       Show log information only"
            echo "  resources  Show system resources only"
            echo "  urls       Show access URLs only"
            echo "  help       Show this help message"
            echo ""
            ;;
            
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
