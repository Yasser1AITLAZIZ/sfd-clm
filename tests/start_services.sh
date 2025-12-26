#!/bin/bash
# Script to start all services for testing

echo "=========================================="
echo "Starting OptiClaims Services for Testing"
echo "=========================================="
echo ""

# SQLite is included in Python, no additional setup needed
echo "✅ SQLite session storage ready (backend-mcp/data/ will be created automatically)"
echo ""

# Start Mock Salesforce service
echo "Starting Mock Salesforce service on port 8001..."
cd mock-salesforce
uvicorn app.main:app --port 8001 --reload &
MOCK_SF_PID=$!
cd ..
sleep 3

# Check if Mock Salesforce started
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Mock Salesforce service started (PID: $MOCK_SF_PID)"
else
    echo "❌ Failed to start Mock Salesforce service"
    kill $MOCK_SF_PID 2>/dev/null
    exit 1
fi

echo ""

# Start Backend MCP service
echo "Starting Backend MCP service on port 8000..."
cd backend-mcp
uvicorn app.main:app --port 8000 --reload &
MCP_PID=$!
cd ..
sleep 3

# Check if Backend MCP started
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend MCP service started (PID: $MCP_PID)"
else
    echo "❌ Failed to start Backend MCP service"
    kill $MOCK_SF_PID $MCP_PID 2>/dev/null
    exit 1
fi

echo ""
echo "=========================================="
echo "All services are running!"
echo "=========================================="
echo ""
echo "Mock Salesforce: http://localhost:8001"
echo "Backend MCP: http://localhost:8000"
echo ""
echo "PIDs:"
echo "  Mock Salesforce: $MOCK_SF_PID"
echo "  Backend MCP: $MCP_PID"
echo ""
echo "To stop services, run:"
echo "  kill $MOCK_SF_PID $MCP_PID"
echo ""
echo "Or use: ./tests/stop_services.sh"
echo ""

# Save PIDs to file
echo "$MOCK_SF_PID $MCP_PID" > .test_services.pid

echo "Ready for testing! Run: python tests/test_pipeline_simple.py"

