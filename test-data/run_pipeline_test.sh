#!/bin/bash
# Script to run the complete pipeline test

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

echo "=========================================="
echo "Pipeline End-to-End Test"
echo "=========================================="
echo ""

# Check if services are already running
echo "Checking if services are running..."
SERVICES_RUNNING=true

if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    SERVICES_RUNNING=false
fi
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    SERVICES_RUNNING=false
fi
if ! curl -s http://localhost:8002/health > /dev/null 2>&1; then
    SERVICES_RUNNING=false
fi

if [ "$SERVICES_RUNNING" = false ]; then
    echo "⚠️  Some services are not running. Starting them..."
    echo ""
    "$SCRIPT_DIR/start_services.sh"
    echo ""
    echo "Waiting for services to be ready..."
    sleep 5
else
    echo "✅ All services are already running"
    echo ""
fi

# Run the test
echo "Running pipeline test..."
echo ""
python "$SCRIPT_DIR/test_pipeline.py"
TEST_EXIT_CODE=$?

echo ""

# Ask if user wants to stop services
if [ "$SERVICES_RUNNING" = false ]; then
    read -p "Do you want to stop the services? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "$SCRIPT_DIR/stop_services.sh"
    fi
fi

exit $TEST_EXIT_CODE

