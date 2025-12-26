#!/bin/bash
# Script to verify that the setup is correct
# Usage: ./verify_setup.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}OptiClaims - Setup Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

ALL_OK=true

# Check Python
echo -e "${YELLOW}Checking Python...${NC}"
if command -v python3 > /dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 3 not found${NC}"
    ALL_OK=false
fi

# Check services
SERVICES=("backend-mcp" "backend-langgraph" "mock-salesforce")
for service in "${SERVICES[@]}"; do
    echo -e "${YELLOW}Checking $service...${NC}"
    SERVICE_DIR="$SCRIPT_DIR/$service"
    VENV_DIR="$SERVICE_DIR/venv"
    
    if [ ! -d "$SERVICE_DIR" ]; then
        echo -e "  ${RED}❌ Service directory not found${NC}"
        ALL_OK=false
        continue
    fi
    
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "  ${RED}❌ Virtual environment not found${NC}"
        echo -e "     Run: ./setup_venv.sh"
        ALL_OK=false
        continue
    fi
    
    if [ ! -f "$SERVICE_DIR/requirements.txt" ]; then
        echo -e "  ${YELLOW}⚠️  No requirements.txt found${NC}"
    else
        echo -e "  ${GREEN}✅ Virtual environment exists${NC}"
        echo -e "  ${GREEN}✅ requirements.txt found${NC}"
    fi
done

# Check test-data
echo -e "${YELLOW}Checking test-data...${NC}"
TEST_DATA_DIR="$SCRIPT_DIR/test-data"
if [ -d "$TEST_DATA_DIR" ]; then
    DOCUMENTS_DIR="$TEST_DATA_DIR/documents"
    FIELDS_FILE="$TEST_DATA_DIR/fields/fields.json"
    
    if [ -d "$DOCUMENTS_DIR" ]; then
        PDF_COUNT=$(find "$DOCUMENTS_DIR" -name "*.pdf" | wc -l)
        if [ "$PDF_COUNT" -gt 0 ]; then
            echo -e "  ${GREEN}✅ Documents directory with $PDF_COUNT PDF file(s)${NC}"
        else
            echo -e "  ${YELLOW}⚠️  Documents directory exists but no PDF files${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠️  Documents directory not found${NC}"
    fi
    
    if [ -f "$FIELDS_FILE" ]; then
        echo -e "  ${GREEN}✅ Fields file found${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Fields file not found${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  test-data directory not found${NC}"
fi

echo ""
if [ "$ALL_OK" = true ]; then
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 0
else
    echo -e "${BLUE}========================================${NC}"
    echo -e "${RED}❌ Some checks failed${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 1
fi

