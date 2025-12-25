#!/bin/bash
# Script to start all services for testing

echo "=========================================="
echo "Starting OptiClaims Services for Testing"
echo "=========================================="
echo ""

# Check if Redis is running
echo "Checking Redis..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "⚠️  Redis is not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis started successfully"
    else
        echo "❌ Failed to start Redis. Please start it manually."
        exit 1
    fi
fi

echo ""

# Create logs directory
LOGS_DIR="$(dirname "$0")/results/logs"
mkdir -p "$LOGS_DIR"

# Start Mock Salesforce service
echo "Starting Mock Salesforce service on port 8001..."
cd "$(dirname "$0")/../mock-salesforce" || exit 1
uvicorn app.main:app --port 8001 --reload > "$LOGS_DIR/mock-salesforce.log" 2>&1 &
MOCK_SF_PID=$!
cd - > /dev/null || exit 1
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
cd "$(dirname "$0")/../backend-mcp" || exit 1
uvicorn app.main:app --port 8000 --reload > "$LOGS_DIR/backend-mcp.log" 2>&1 &
MCP_PID=$!
cd - > /dev/null || exit 1
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

# Start Backend LangGraph service
echo "Starting Backend LangGraph service on port 8002..."
cd "$(dirname "$0")/../backend-langgraph" || exit 1
uvicorn app.main:app --port 8002 --reload > "$LOGS_DIR/backend-langgraph.log" 2>&1 &
LANGGRAPH_PID=$!
cd - > /dev/null || exit 1
sleep 3

# Check if Backend LangGraph started
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "✅ Backend LangGraph service started (PID: $LANGGRAPH_PID)"
else
    echo "❌ Failed to start Backend LangGraph service"
    kill $MOCK_SF_PID $MCP_PID $LANGGRAPH_PID 2>/dev/null
    exit 1
fi

echo ""
echo "=========================================="
echo "All services are running!"
echo "=========================================="
echo ""
echo "Mock Salesforce: http://localhost:8001"
echo "Backend MCP: http://localhost:8000"
echo "Backend LangGraph: http://localhost:8002"
echo ""
echo "PIDs:"
echo "  Mock Salesforce: $MOCK_SF_PID"
echo "  Backend MCP: $MCP_PID"
echo "  Backend LangGraph: $LANGGRAPH_PID"
echo ""
echo "Logs are being written to: $LOGS_DIR"
echo ""
echo "To stop services, run:"
echo "  kill $MOCK_SF_PID $MCP_PID $LANGGRAPH_PID"
echo ""
echo "Or use: ./test-data/stop_services.sh"
echo ""

# Save PIDs to file
PID_FILE="$(dirname "$0")/.test_services.pid"
echo "$MOCK_SF_PID $MCP_PID $LANGGRAPH_PID" > "$PID_FILE"

echo "Ready for testing! Run: python test-data/test_pipeline.py"
echo ""

