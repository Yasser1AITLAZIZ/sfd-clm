#!/bin/bash
# Script to run the complete pipeline test with Docker Compose (Linux/Mac)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Pipeline End-to-End Test (Docker)"
echo "=========================================="
echo ""

# Check if Docker is running
echo "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running. Please start Docker and try again."
    exit 1
fi
echo "[OK] Docker is running"

# Check if docker-compose is available
echo "Checking docker-compose..."
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "[ERROR] docker-compose is not available. Please install docker-compose."
    exit 1
fi
echo "[OK] docker-compose is available"

echo ""

# Check if services are already running
echo "Checking if services are running..."
SERVICES_RUNNING=true

if ! curl -f -s http://localhost:8001/health > /dev/null 2>&1; then
    SERVICES_RUNNING=false
fi

if ! curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    SERVICES_RUNNING=false
fi

if ! curl -f -s http://localhost:8002/health > /dev/null 2>&1; then
    SERVICES_RUNNING=false
fi

if [ "$SERVICES_RUNNING" = false ]; then
    echo "[INFO] Starting Docker services..."
    echo ""
    
    # Build and start services
    docker-compose up -d --build
    
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to start Docker services"
        exit 1
    fi
    
    echo ""
    echo "Waiting for services to be ready..."
    
    # Wait for services with timeout
    MAX_WAIT=60
    WAITED=0
    ALL_READY=false
    
    while [ $WAITED -lt $MAX_WAIT ] && [ "$ALL_READY" = false ]; do
        sleep 2
        WAITED=$((WAITED + 2))
        
        ALL_READY=true
        if ! curl -f -s http://localhost:8001/health > /dev/null 2>&1; then
            ALL_READY=false
        fi
        
        if ! curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            ALL_READY=false
        fi
        
        if ! curl -f -s http://localhost:8002/health > /dev/null 2>&1; then
            ALL_READY=false
        fi
        
        if [ "$ALL_READY" = false ]; then
            echo "  Waiting for services... ($WAITED/$MAX_WAIT seconds)"
        fi
    done
    
    if [ "$ALL_READY" = false ]; then
        echo "[ERROR] Services did not become ready within $MAX_WAIT seconds"
        echo "Checking service logs..."
        docker-compose logs --tail=50
        exit 1
    fi
    
    echo "[OK] All services are ready"
    echo ""
else
    echo "[OK] All services are already running"
    echo ""
fi

# Run the test
echo "Running pipeline test..."
echo ""
python3 "$SCRIPT_DIR/test_pipeline.py"
TEST_EXIT_CODE=$?

echo ""

# Ask if user wants to stop services
read -p "Do you want to stop the Docker services? (y/N): " response
if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    echo "Stopping Docker services..."
    docker-compose down
    echo "[OK] Services stopped"
fi

exit $TEST_EXIT_CODE

