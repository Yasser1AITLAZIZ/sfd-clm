#!/bin/bash
# Script to view and filter logs

LOGS_DIR="$(dirname "$0")/results/logs"

if [ ! -d "$LOGS_DIR" ]; then
    echo "❌ Logs directory not found: $LOGS_DIR"
    exit 1
fi

echo "Available log files:"
ls -lh "$LOGS_DIR"/*.log 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""

if [ $# -eq 0 ]; then
    echo "Usage: $0 [service] [filter]"
    echo ""
    echo "Services: mock-salesforce, backend-mcp, backend-langgraph, all"
    echo "Filters: error, workflow_id=<id>, record_id=<id>"
    echo ""
    echo "Examples:"
    echo "  $0 backend-mcp                    # Show all backend-mcp logs"
    echo "  $0 all error                     # Show all errors"
    echo "  $0 backend-mcp workflow_id=xxx    # Filter by workflow_id"
    exit 0
fi

SERVICE=$1
FILTER=$2

if [ "$SERVICE" = "all" ]; then
    FILES="$LOGS_DIR/*.log"
else
    FILES="$LOGS_DIR/${SERVICE}.log"
fi

if [ -z "$FILTER" ]; then
    # Show all logs
    for file in $FILES; do
        if [ -f "$file" ]; then
            echo "=== $(basename $file) ==="
            tail -n 50 "$file"
            echo ""
        fi
    done
elif [ "$FILTER" = "error" ]; then
    # Filter errors
    for file in $FILES; do
        if [ -f "$file" ]; then
            echo "=== Errors in $(basename $file) ==="
            grep -i "error\|failed\|exception" "$file" | tail -n 20
            echo ""
        fi
    done
elif [[ "$FILTER" == workflow_id=* ]]; then
    # Filter by workflow_id
    WORKFLOW_ID="${FILTER#workflow_id=}"
    for file in $FILES; do
        if [ -f "$file" ]; then
            echo "=== Workflow $WORKFLOW_ID in $(basename $file) ==="
            grep "$WORKFLOW_ID" "$file"
            echo ""
        fi
    done
elif [[ "$FILTER" == record_id=* ]]; then
    # Filter by record_id
    RECORD_ID="${FILTER#record_id=}"
    for file in $FILES; do
        if [ -f "$file" ]; then
            echo "=== Record $RECORD_ID in $(basename $file) ==="
            grep "$RECORD_ID" "$file"
            echo ""
        fi
    done
else
    echo "Unknown filter: $FILTER"
    exit 1
fi

