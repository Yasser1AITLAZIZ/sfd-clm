#!/bin/bash
# Script to start all services for testing

echo "=========================================="
echo "Starting OptiClaims Services for Testing"
echo "=========================================="
echo ""

# Create logs directory
LOGS_DIR="$(dirname "$0")/results/logs"
mkdir -p "$LOGS_DIR"

# Create data directory for SQLite
DATA_DIR="$(dirname "$0")/../backend-mcp/data"
mkdir -p "$DATA_DIR"
echo "✅ Data directory ready for SQLite"
echo ""

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
LANGGRAPH_DIR="$(dirname "$0")/../backend-langgraph"
cd "$LANGGRAPH_DIR" || exit 1

# Create .env file for LangGraph with MOCK_MODE enabled if it doesn't exist
LANGGRAPH_ENV_FILE="$LANGGRAPH_DIR/.env"
if [ ! -f "$LANGGRAPH_ENV_FILE" ]; then
    echo "  Creating .env file with MOCK_MODE=true for testing..."
    cat > "$LANGGRAPH_ENV_FILE" << EOF
# Backend LangGraph Configuration (Auto-generated for testing)
LOG_LEVEL=INFO
DEBUG=false
HOST=0.0.0.0
PORT=8002
MOCK_MODE=true
EOF
    echo "  ✅ .env file created with MOCK_MODE=true"
else
    # Check if MOCK_MODE is set, if not add it
    if ! grep -q "MOCK_MODE" "$LANGGRAPH_ENV_FILE"; then
        echo "  Adding MOCK_MODE=true to existing .env file..."
        echo "" >> "$LANGGRAPH_ENV_FILE"
        echo "MOCK_MODE=true" >> "$LANGGRAPH_ENV_FILE"
        echo "  ✅ MOCK_MODE=true added to .env file"
    fi
fi

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

