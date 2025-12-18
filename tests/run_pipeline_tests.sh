#!/bin/bash
# Script to run pipeline tests

echo "=========================================="
echo "OptiClaims Pipeline E2E Tests"
echo "=========================================="
echo ""

# Check if services are running
echo "Checking if services are running..."
echo ""

# Check mock-salesforce
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Mock Salesforce service is running on port 8001"
else
    echo "❌ Mock Salesforce service is NOT running on port 8001"
    echo "   Please start it with: cd mock-salesforce && uvicorn app.main:app --port 8001"
    exit 1
fi

# Check backend-mcp
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend MCP service is running on port 8000"
else
    echo "❌ Backend MCP service is NOT running on port 8000"
    echo "   Please start it with: cd backend-mcp && uvicorn app.main:app --port 8000"
    exit 1
fi

echo ""
echo "Running pipeline tests..."
echo ""

# Run tests
python -m pytest tests/test_pipeline_e2e.py -v

# Or run directly with Python
# python tests/test_pipeline_e2e.py

echo ""
echo "Tests completed!"
echo "Check test_results.json for detailed results"

