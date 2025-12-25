#!/bin/bash
# Script to stop all test services

echo "Stopping test services..."

PID_FILE="$(dirname "$0")/.test_services.pid"

if [ -f "$PID_FILE" ]; then
    PIDS=$(cat "$PID_FILE")
    if [ -n "$PIDS" ]; then
        echo "Killing processes: $PIDS"
        kill $PIDS 2>/dev/null
        sleep 2
        
        # Force kill if still running
        for pid in $PIDS; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "Force killing PID $pid"
                kill -9 "$pid" 2>/dev/null
            fi
        done
        
        rm -f "$PID_FILE"
        echo "✅ Services stopped"
    else
        echo "⚠️  No PIDs found in $PID_FILE"
    fi
else
    echo "⚠️  PID file not found: $PID_FILE"
    echo "Trying to find and kill services by port..."
    
    # Try to find processes by port
    for port in 8000 8001 8002; do
        PID=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$PID" ]; then
            echo "Killing process on port $port (PID: $PID)"
            kill $PID 2>/dev/null
        fi
    done
fi

echo "Done"

