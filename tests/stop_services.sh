#!/bin/bash
# Script to stop all test services

echo "Stopping OptiClaims test services..."

if [ -f .test_services.pid ]; then
    PIDS=$(cat .test_services.pid)
    kill $PIDS 2>/dev/null
    rm .test_services.pid
    echo "✅ Services stopped"
else
    echo "⚠️  No PID file found. Trying to find and kill processes..."
    
    # Try to find and kill by port
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    lsof -ti:8001 | xargs kill -9 2>/dev/null
    
    echo "✅ Attempted to stop services on ports 8000 and 8001"
fi

