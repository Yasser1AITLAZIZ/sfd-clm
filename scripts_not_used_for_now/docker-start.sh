#!/bin/bash
# Quick start script for Docker Compose (Linux/Mac)
# This script starts all services and waits for them to be ready

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Starting SFD-CLM Services with Docker"
echo "=========================================="
echo ""

# Check Docker
echo "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running. Please start Docker."
    exit 1
fi
echo "[OK] Docker is running"

# Build and start services
echo ""
echo "Building and starting services..."
docker-compose up -d --build

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to start services"
    exit 1
fi

echo ""
echo "Waiting for services to be ready..."

# Wait for services
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
        echo "  Waiting... ($WAITED/$MAX_WAIT seconds)"
    fi
done

if [ "$ALL_READY" = true ]; then
    echo ""
    echo "[OK] All services are ready!"
    echo ""
    echo "Services:"
    echo "  - Mock Salesforce:  http://localhost:8001"
    echo "  - Backend MCP:      http://localhost:8000"
    echo "  - Backend LangGraph: http://localhost:8002"
    echo ""
    echo "Useful commands:"
    echo "  - View logs:        docker-compose logs -f"
    echo "  - Stop services:    docker-compose down"
    echo "  - Restart service:  docker-compose restart <service-name>"
    echo ""
else
    echo ""
    echo "[ERROR] Services did not become ready within $MAX_WAIT seconds"
    echo "Check logs with: docker-compose logs"
    exit 1
fi

