#!/bin/bash

# Deployment Verification Script
# Ensures all required files exist before deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Verifying Deployment Readiness${NC}"
echo "=================================="

# Check required files
REQUIRED_FILES=(
    ".env.example"
    "docker-compose.yml"
    "schema.sql"
    "database/init.sql"
    "database/mongo-init.js"
    "monitoring/prometheus.yml"
    "monitoring/grafana/provisioning/datasources/prometheus.yml"
    "monitoring/grafana/provisioning/dashboards/dashboards.yml"
    "monitoring/grafana/dashboards/kyc-system-overview.json"
    "configs/default.yaml"
    "configs/client_override.yaml"
    "rust-core/Cargo.toml"
    "rust-core/src/main.rs"
    "rust-core/Dockerfile"
    "rust-core/migrations/001_initial.sql"
    "scripts/deploy.sh"
    "tests/test_runner.py"
    "action_list.md"
    "README.md"
)

# Check Python agents
PYTHON_AGENTS=(
    "data-ingestion-agent"
    "kyc-analysis-agent"
    "decision-making-agent"
    "compliance-monitoring-agent"
    "data-quality-agent"
)

missing_files=()

echo -e "${BLUE}Checking core files...${NC}"
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ✅ $file"
    else
        echo -e "  ❌ $file"
        missing_files+=("$file")
    fi
done

echo -e "\n${BLUE}Checking Python agents...${NC}"
for agent in "${PYTHON_AGENTS[@]}"; do
    agent_dir="python-agents/$agent"
    # Convert agent name to service file name (remove -agent suffix and replace - with _)
    service_name=$(echo "$agent" | sed 's/-agent$//' | sed 's/-/_/g')
    service_file="$agent_dir/${service_name}_service.py"
    requirements_file="$agent_dir/requirements.txt"
    dockerfile="$agent_dir/Dockerfile"
    
    if [ -f "$service_file" ]; then
        echo -e "  ✅ $service_file"
    else
        echo -e "  ❌ $service_file"
        missing_files+=("$service_file")
    fi
    
    if [ -f "$requirements_file" ]; then
        echo -e "  ✅ $requirements_file"
    else
        echo -e "  ❌ $requirements_file"
        missing_files+=("$requirements_file")
    fi
    
    if [ -f "$dockerfile" ]; then
        echo -e "  ✅ $dockerfile"
    else
        echo -e "  ❌ $dockerfile"
        missing_files+=("$dockerfile")
    fi
done

echo -e "\n${BLUE}Checking UI files...${NC}"
UI_FILES=(
    "rust-core/src/ui/templates/index.html"
    "rust-core/src/ui/templates/userguide.html"
    "rust-core/src/ui/static/style.css"
    "rust-core/src/ui/static/app.js"
)

for file in "${UI_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ✅ $file"
    else
        echo -e "  ❌ $file"
        missing_files+=("$file")
    fi
done

echo -e "\n${BLUE}Checking directory structure...${NC}"
REQUIRED_DIRS=(
    "configs"
    "database"
    "monitoring/grafana/provisioning/datasources"
    "monitoring/grafana/provisioning/dashboards"
    "monitoring/grafana/dashboards"
    "python-agents"
    "rust-core/src"
    "rust-core/migrations"
    "scripts"
    "tests"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ✅ $dir/"
    else
        echo -e "  ❌ $dir/"
        missing_files+=("$dir/")
    fi
done

# Validate Docker Compose
echo -e "\n${BLUE}Validating Docker Compose configuration...${NC}"
if docker-compose config > /dev/null 2>&1; then
    echo -e "  ✅ docker-compose.yml is valid"
else
    echo -e "  ❌ docker-compose.yml has errors"
    missing_files+=("docker-compose.yml (invalid)")
fi

# Check file sizes (ensure they're not empty)
echo -e "\n${BLUE}Checking file sizes...${NC}"
CRITICAL_FILES=(
    "rust-core/src/main.rs"
    "python-agents/data-ingestion-agent/data_ingestion_service.py"
    "python-agents/kyc-analysis-agent/kyc_analysis_service.py"
    "python-agents/decision-making-agent/decision_making_service.py"
    "python-agents/compliance-monitoring-agent/compliance_monitoring_service.py"
    "python-agents/data-quality-agent/data_quality_service.py"
    "database/init.sql"
    "monitoring/prometheus.yml"
    ".env.example"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        if [ "$size" -gt 100 ]; then
            echo -e "  ✅ $file ($size bytes)"
        else
            echo -e "  ⚠️  $file ($size bytes - seems too small)"
        fi
    fi
done

# Summary
echo -e "\n${BLUE}=================================="
echo -e "VERIFICATION SUMMARY${NC}"
echo "=================================="

if [ ${#missing_files[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED!${NC}"
    echo -e "${GREEN}✅ System is ready for deployment${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Copy .env.example to .env and configure"
    echo "2. Run: ./scripts/deploy.sh"
    echo "3. Access: http://localhost:8000"
    exit 0
else
    echo -e "${RED}❌ DEPLOYMENT NOT READY${NC}"
    echo -e "${RED}Missing ${#missing_files[@]} required files:${NC}"
    for file in "${missing_files[@]}"; do
        echo -e "  - $file"
    done
    echo ""
    echo -e "${YELLOW}Please create the missing files before deployment.${NC}"
    exit 1
fi
