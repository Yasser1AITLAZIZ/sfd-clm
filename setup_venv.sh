#!/bin/bash
# Script to setup virtual environments and install requirements for all services
# Usage: ./setup_venv.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}OptiClaims - Virtual Environment Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' || echo "not found")
if [ "$PYTHON_VERSION" = "not found" ]; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.10.9 or higher.${NC}"
    exit 1
fi

PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
PYTHON_PATCH=$(echo $PYTHON_VERSION | cut -d. -f3)

# Check if version is 3.10.9+ or 3.11+
IS_VALID=false
if [ "$PYTHON_MAJOR" -gt 3 ]; then
    IS_VALID=true
elif [ "$PYTHON_MAJOR" -eq 3 ]; then
    if [ "$PYTHON_MINOR" -gt 10 ]; then
        IS_VALID=true
    elif [ "$PYTHON_MINOR" -eq 10 ]; then
        # Check patch version for 3.10.x (must be >= 9)
        if [ -n "$PYTHON_PATCH" ] && [ "$PYTHON_PATCH" -ge 9 ]; then
            IS_VALID=true
        fi
    fi
fi

if [ "$IS_VALID" = false ]; then
    echo -e "${RED}❌ Python 3.10.9+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"
echo ""

# Check if venv module is available
echo -e "${YELLOW}Checking venv module...${NC}"
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo -e "${RED}❌ venv module not available. Please install python3-venv.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ venv module available${NC}"
echo ""

# Services to setup
SERVICES=("backend-mcp" "backend-langgraph" "mock-salesforce")

# Function to setup venv for a service
setup_service_venv() {
    local service=$1
    local service_dir="$SCRIPT_DIR/$service"
    local venv_dir="$service_dir/venv"
    
    echo -e "${BLUE}Setting up $service...${NC}"
    
    if [ ! -d "$service_dir" ]; then
        echo -e "${RED}❌ Service directory not found: $service_dir${NC}"
        return 1
    fi
    
    # Create venv if it doesn't exist
    if [ ! -d "$venv_dir" ]; then
        echo -e "  ${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv "$venv_dir"
        echo -e "  ${GREEN}✅ Virtual environment created${NC}"
    else
        echo -e "  ${YELLOW}Virtual environment already exists, skipping creation${NC}"
    fi
    
    # Activate venv and install requirements
    echo -e "  ${YELLOW}Installing requirements...${NC}"
    source "$venv_dir/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip --quiet
    
    # Install requirements
    if [ -f "$service_dir/requirements.txt" ]; then
        pip install -r "$service_dir/requirements.txt"
        echo -e "  ${GREEN}✅ Requirements installed${NC}"
    else
        echo -e "  ${YELLOW}⚠️  No requirements.txt found${NC}"
    fi
    
    deactivate
    echo -e "${GREEN}✅ $service setup complete${NC}"
    echo ""
}

# Setup each service
for service in "${SERVICES[@]}"; do
    setup_service_venv "$service"
done

# Check Redis (optional but recommended)
echo -e "${YELLOW}Checking Redis...${NC}"
if command -v redis-cli > /dev/null 2>&1; then
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis is running${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis is installed but not running${NC}"
        echo -e "   Start Redis with: redis-server"
    fi
else
    echo -e "${YELLOW}⚠️  Redis not found. It's required for session storage.${NC}"
    echo -e "   Install Redis: https://redis.io/docs/getting-started/"
fi
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "To activate a service's virtual environment:"
echo "  cd backend-mcp && source venv/bin/activate"
echo "  cd backend-langgraph && source venv/bin/activate"
echo "  cd mock-salesforce && source venv/bin/activate"
echo ""
echo "To run a service:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload --port <PORT>"
echo ""

