#!/bin/bash
# Script Bash pour exécuter le pipeline réel end-to-end
# Usage: ./run_pipeline_reel.sh [--record-id "001XX000001"] [--user-message "Extract data from documents"]

# Default values
RECORD_ID="${1:-001XX000001}"
USER_MESSAGE="${2:-Extract data from documents}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --record-id)
            RECORD_ID="$2"
            shift 2
            ;;
        --user-message)
            USER_MESSAGE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "=========================================="
echo "Pipeline Réel - Exécution End-to-End"
echo "=========================================="
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Service URLs
MOCK_SALESFORCE_URL="http://localhost:8001"
BACKEND_MCP_URL="http://localhost:8000"
BACKEND_LANGGRAPH_URL="http://localhost:8002"

# Service directories
declare -A SERVICES
SERVICES["Mock Salesforce"]="mock-salesforce:8001"
SERVICES["Backend MCP"]="backend-mcp:8000"
SERVICES["Backend LangGraph"]="backend-langgraph:8002"

# Process IDs to track started services
declare -A SERVICE_PIDS

# Function to check if Python 3.10.9 is installed
check_python_version() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        if echo "$PYTHON_VERSION" | grep -q "Python 3.10.9"; then
            echo "✅ Python 3.10.9 found: $PYTHON_VERSION"
            return 0
        else
            echo "⚠️  Python version: $PYTHON_VERSION (expected 3.10.9)"
            echo "   Continuing anyway..."
            return 0
        fi
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1)
        if echo "$PYTHON_VERSION" | grep -q "Python 3.10.9"; then
            echo "✅ Python 3.10.9 found: $PYTHON_VERSION"
            return 0
        else
            echo "⚠️  Python version: $PYTHON_VERSION (expected 3.10.9)"
            echo "   Continuing anyway..."
            return 0
        fi
    else
        echo "❌ Python not found. Please install Python 3.10.9"
        return 1
    fi
}

# Function to check if a port is available
check_port_available() {
    local port=$1
    if command -v lsof &> /dev/null; then
        lsof -i :$port > /dev/null 2>&1
        return $?
    elif command -v netstat &> /dev/null; then
        netstat -an | grep -q ":$port " && return 1 || return 0
    else
        # Assume port is available if we can't check
        return 0
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_retries=${3:-30}
    local retry_delay=${4:-1.0}
    
    for ((i=0; i<max_retries; i++)); do
        if curl -s -f "$url/health" > /dev/null 2>&1; then
            echo "✅ $service_name is ready"
            return 0
        fi
        
        if [ $i -lt $((max_retries - 1)) ]; then
            sleep $retry_delay
        fi
    done
    
    echo "❌ $service_name is not ready after $((max_retries * retry_delay))s"
    return 1
}

# Function to start a service
start_service() {
    local service_name=$1
    local service_dir=$2
    local port=$3
    
    local venv_python="$service_dir/venv/bin/python"
    
    if [ ! -f "$venv_python" ]; then
        echo "❌ Virtual environment not found for $service_name"
        echo "   Expected: $venv_python"
        echo "   Please run: ./setup_venv.sh"
        return 1
    fi
    
    # Check if port is available
    if ! check_port_available $port; then
        echo "⚠️  Port $port is already in use. Assuming service is already running."
        return 0
    fi
    
    echo "Starting $service_name on port $port..."
    
    cd "$service_dir" || return 1
    "$venv_python" -m uvicorn app.main:app --port $port --reload > /dev/null 2>&1 &
    local pid=$!
    cd "$PROJECT_ROOT" || return 1
    
    if [ $pid -gt 0 ]; then
        echo "✅ $service_name started (PID: $pid)"
        SERVICE_PIDS["$service_name"]=$pid
        sleep 2
        return 0
    else
        echo "❌ Failed to start $service_name"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local pid=$1
    local service_name=$2
    
    if [ -n "$pid" ] && kill -0 $pid 2>/dev/null; then
        echo "Stopping $service_name..."
        kill $pid 2>/dev/null
        wait $pid 2>/dev/null
        echo "✅ $service_name stopped"
    fi
}

# Step 1: Check prerequisites
echo "Step 1: Checking prerequisites..."
echo ""

if ! check_python_version; then
    exit 1
fi

# Check venvs
ALL_VENVS_EXIST=true
for service_name in "${!SERVICES[@]}"; do
    IFS=':' read -r service_dir port <<< "${SERVICES[$service_name]}"
    venv_path="$PROJECT_ROOT/$service_dir/venv/bin/python"
    if [ ! -f "$venv_path" ]; then
        echo "❌ $service_name venv not found: $venv_path"
        ALL_VENVS_EXIST=false
    fi
done

if [ "$ALL_VENVS_EXIST" = false ]; then
    echo ""
    echo "[ERROR] Some virtual environments are missing!"
    echo "        Please run: ./setup_venv.sh"
    exit 1
fi

echo "✅ All prerequisites met"
echo ""

# Step 2: Start services
echo "Step 2: Starting services..."
echo ""

for service_name in "${!SERVICES[@]}"; do
    IFS=':' read -r service_dir port <<< "${SERVICES[$service_name]}"
    full_service_dir="$PROJECT_ROOT/$service_dir"
    start_service "$service_name" "$full_service_dir" "$port"
done

echo ""

# Step 3: Wait for services to be ready
echo "Step 3: Waiting for services to be ready..."
echo ""

ALL_SERVICES_READY=true
wait_for_service "$MOCK_SALESFORCE_URL" "Mock Salesforce" || ALL_SERVICES_READY=false
wait_for_service "$BACKEND_MCP_URL" "Backend MCP" || ALL_SERVICES_READY=false
wait_for_service "$BACKEND_LANGGRAPH_URL" "Backend LangGraph" || ALL_SERVICES_READY=false

if [ "$ALL_SERVICES_READY" = false ]; then
    echo ""
    echo "[ERROR] Some services are not ready. Please check the logs."
    echo "        Stopping started services..."
    
    for service_name in "${!SERVICE_PIDS[@]}"; do
        stop_service "${SERVICE_PIDS[$service_name]}" "$service_name"
    done
    
    exit 1
fi

echo ""

# Step 4: Execute pipeline
echo "Step 4: Executing pipeline..."
echo "   Record ID: $RECORD_ID"
echo "   User Message: $USER_MESSAGE"
echo ""

START_TIME=$(date +%s)

PAYLOAD=$(cat <<EOF
{
  "record_id": "$RECORD_ID",
  "session_id": null,
  "user_message": "$USER_MESSAGE"
}
EOF
)

echo "📤 Sending request to Backend MCP..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BACKEND_MCP_URL/api/mcp/receive-request" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    --max-time 300)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))

if [ "$HTTP_CODE" -eq 200 ]; then
    echo "✅ Pipeline completed in ${ELAPSED_TIME}s"
    echo ""
    
    # Display results
    echo "=========================================="
    echo "RESULTS"
    echo "=========================================="
    echo ""
    
    # Parse JSON response (requires jq or basic parsing)
    if command -v jq &> /dev/null; then
        STATUS=$(echo "$BODY" | jq -r '.status // "unknown"')
        
        if [ "$STATUS" = "success" ]; then
            WORKFLOW_STATUS=$(echo "$BODY" | jq -r '.data.status // "unknown"')
            WORKFLOW_ID=$(echo "$BODY" | jq -r '.data.workflow_id // "unknown"')
            
            echo "Status: $WORKFLOW_STATUS"
            echo "Workflow ID: $WORKFLOW_ID"
            echo ""
            
            # Extract extracted data
            EXTRACTED_DATA=$(echo "$BODY" | jq -r '.data.data.response_handling.extracted_data // .data.data.mcp_sending.mcp_response.extracted_data // {}')
            CONFIDENCE_SCORES=$(echo "$BODY" | jq -r '.data.data.response_handling.confidence_scores // .data.data.mcp_sending.mcp_response.confidence_scores // {}')
            
            FIELD_COUNT=$(echo "$EXTRACTED_DATA" | jq 'length')
            
            if [ "$FIELD_COUNT" -gt 0 ]; then
                echo "Extracted Data ($FIELD_COUNT fields):"
                echo "------------------------------------------------------------"
                
                echo "$EXTRACTED_DATA" | jq -r 'to_entries[] | "  \(.key): \(.value)"'
                
                if [ -n "$CONFIDENCE_SCORES" ] && [ "$CONFIDENCE_SCORES" != "{}" ]; then
                    AVG_CONFIDENCE=$(echo "$CONFIDENCE_SCORES" | jq '[.[]] | add / length')
                    echo ""
                    printf "Average Confidence: %.2f%%\n" $(echo "$AVG_CONFIDENCE * 100" | bc -l)
                fi
            else
                echo "⚠️  No extracted data found in response"
            fi
        else
            echo "Status: $STATUS"
            ERROR_MSG=$(echo "$BODY" | jq -r '.error.message // "Unknown error"')
            echo "Error: $ERROR_MSG"
        fi
    else
        # Basic parsing without jq
        echo "Response received (install 'jq' for better formatting):"
        echo "$BODY" | head -20
    fi
    
    echo ""
    echo "=========================================="
else
    echo "❌ Pipeline execution failed (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
fi

echo ""

# Step 5: Cleanup
echo "Step 5: Cleaning up..."
echo ""

for service_name in "${!SERVICE_PIDS[@]}"; do
    stop_service "${SERVICE_PIDS[$service_name]}" "$service_name"
done

echo ""
echo "=========================================="
echo "Pipeline execution completed"
echo "=========================================="
echo ""

