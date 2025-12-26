#!/bin/bash
# Script to view and filter logs - Enhanced version with traceback support

LOGS_DIR="$(dirname "$0")/results/logs"

if [ ! -d "$LOGS_DIR" ]; then
    echo "❌ Logs directory not found: $LOGS_DIR"
    exit 1
fi

echo "Available log files:"
ls -lh "$LOGS_DIR"/*.log 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""

if [ $# -eq 0 ]; then
    echo "Usage: $0 [service] [filter] [options]"
    echo ""
    echo "Services: mock-salesforce, backend-mcp, backend-langgraph, all"
    echo "Filters: error, traceback, workflow_id=<id>, record_id=<id>"
    echo "Options: verbose, stderr"
    echo ""
    echo "Examples:"
    echo "  $0 backend-mcp                    # Show last 100 lines"
    echo "  $0 all error                     # Show all errors with context"
    echo "  $0 backend-mcp traceback          # Show tracebacks only"
    echo "  $0 backend-mcp error verbose     # Show errors with full details"
    echo "  $0 backend-mcp error stderr         # Include stderr.log files"
    echo "  $0 backend-mcp workflow_id=xxx    # Filter by workflow_id"
    exit 0
fi

SERVICE=$1
FILTER=$2
OPTIONS="${@:3}"

# Check for options
VERBOSE=false
INCLUDE_STDERR=false

for opt in $OPTIONS; do
    case $opt in
        verbose)
            VERBOSE=true
            ;;
        stderr)
            INCLUDE_STDERR=true
            ;;
    esac
done

# Get log files
if [ "$SERVICE" = "all" ]; then
    if [ "$INCLUDE_STDERR" = true ]; then
        FILES="$LOGS_DIR/*.log"
    else
        FILES=$(ls "$LOGS_DIR"/*.log 2>/dev/null | grep -v "\.stderr\.log$")
    fi
else
    FILES="$LOGS_DIR/${SERVICE}.log"
    if [ "$INCLUDE_STDERR" = true ]; then
        STDERR_FILES="$LOGS_DIR/${SERVICE}.stderr.log"
    fi
fi

if [ -z "$FILES" ] && [ -z "$STDERR_FILES" ]; then
    echo "❌ No log files found"
    exit 1
fi

show_error_with_context() {
    local file="$1"
    local context_lines=${2:-5}
    
    if [ ! -f "$file" ]; then
        return
    fi
    
    local line_num=0
    local in_error=false
    
    while IFS= read -r line; do
        line_num=$((line_num + 1))
        
        if echo "$line" | grep -qiE "error|failed|exception|traceback" && ! echo "$line" | grep -qE "INFO|DEBUG"; then
            in_error=true
            local start=$((line_num - context_lines))
            local end=$((line_num + context_lines))
            
            if [ $start -gt 0 ]; then
                echo "  ..."
            fi
            
            # Show context lines
            local i=$start
            while [ $i -le $end ] && [ $i -le $(wc -l < "$file") ]; do
                if [ $i -gt 0 ]; then
                    local context_line=$(sed -n "${i}p" "$file")
                    if [ $i -eq $line_num ]; then
                        # Error line - highlight in red
                        echo -e "  [$i] \033[31m$context_line\033[0m"
                    elif echo "$context_line" | grep -qiE "traceback|Traceback"; then
                        # Traceback line - highlight in yellow
                        echo -e "  [$i] \033[33m$context_line\033[0m"
                    else
                        # Context line
                        echo -e "  [$i] \033[90m$context_line\033[0m"
                    fi
                fi
                i=$((i + 1))
            done
            
            local total_lines=$(wc -l < "$file")
            if [ $end -lt $total_lines ]; then
                echo "  ..."
            fi
            echo ""
        fi
    done < "$file"
}

show_traceback() {
    local file="$1"
    
    if [ ! -f "$file" ]; then
        return
    fi
    
    local in_traceback=false
    local traceback_lines=()
    local line_num=0
    
    while IFS= read -r line; do
        line_num=$((line_num + 1))
        
        if echo "$line" | grep -qiE "Traceback|traceback"; then
            in_traceback=true
            traceback_lines=("$line")
        elif [ "$in_traceback" = true ]; then
            if echo "$line" | grep -qE "^\s+File |^\s+at |^\s+in |^\s+raise |^\s+Exception:"; then
                traceback_lines+=("$line")
            elif [ -z "$(echo "$line" | tr -d '[:space:]')" ] || echo "$line" | grep -qE "^\d{4}-\d{2}-\d{2}"; then
                # End of traceback
                if [ ${#traceback_lines[@]} -gt 0 ]; then
                    echo -e "  \033[33mTraceback found at line $((line_num - ${#traceback_lines[@]} + 1)):\033[0m"
                    for tb_line in "${traceback_lines[@]}"; do
                        echo -e "    \033[33m$tb_line\033[0m"
                    done
                    echo ""
                fi
                in_traceback=false
                traceback_lines=()
            else
                traceback_lines+=("$line")
            fi
        fi
    done < "$file"
    
    # Handle traceback at end of file
    if [ "$in_traceback" = true ] && [ ${#traceback_lines[@]} -gt 0 ]; then
        echo -e "  \033[33mTraceback found at end of file:\033[0m"
        for tb_line in "${traceback_lines[@]}"; do
            echo -e "    \033[33m$tb_line\033[0m"
        done
        echo ""
    fi
}

if [ -z "$FILTER" ]; then
    # Show all logs - increased to 100 lines
    for file in $FILES; do
        if [ -f "$file" ]; then
            echo -e "\033[36m=== $(basename $file) ===\033[0m"
            tail -n 100 "$file"
            echo ""
        fi
    done
    
    if [ "$INCLUDE_STDERR" = true ] && [ -n "$STDERR_FILES" ]; then
        for file in $STDERR_FILES; do
            if [ -f "$file" ]; then
                echo -e "\033[35m=== $(basename $file) ===\033[0m"
                tail -n 100 "$file"
                echo ""
            fi
        done
    fi
elif [ "$FILTER" = "error" ]; then
    # Filter errors with context
    for file in $FILES; do
        if [ -f "$file" ]; then
            echo -e "\033[36m=== Errors in $(basename $file) ===\033[0m"
            if [ "$VERBOSE" = true ]; then
                show_error_with_context "$file" 10
            else
                show_error_with_context "$file" 5
            fi
            echo ""
        fi
    done
    
    if [ "$INCLUDE_STDERR" = true ] && [ -n "$STDERR_FILES" ]; then
        for file in $STDERR_FILES; do
            if [ -f "$file" ]; then
                echo -e "\033[35m=== Errors in $(basename $file) ===\033[0m"
                if [ "$VERBOSE" = true ]; then
                    show_error_with_context "$file" 10
                else
                    show_error_with_context "$file" 5
                fi
                echo ""
            fi
        done
    fi
elif [ "$FILTER" = "traceback" ]; then
    # Show only tracebacks
    for file in $FILES; do
        if [ -f "$file" ]; then
            echo -e "\033[36m=== Tracebacks in $(basename $file) ===\033[0m"
            show_traceback "$file"
            echo ""
        fi
    done
    
    if [ "$INCLUDE_STDERR" = true ] && [ -n "$STDERR_FILES" ]; then
        for file in $STDERR_FILES; do
            if [ -f "$file" ]; then
                echo -e "\033[35m=== Tracebacks in $(basename $file) ===\033[0m"
                show_traceback "$file"
                echo ""
            fi
        done
    fi
elif [[ "$FILTER" == workflow_id=* ]]; then
    # Filter by workflow_id
    WORKFLOW_ID="${FILTER#workflow_id=}"
    for file in $FILES; do
        if [ -f "$file" ]; then
            echo -e "\033[36m=== Workflow $WORKFLOW_ID in $(basename $file) ===\033[0m"
            grep -n "$WORKFLOW_ID" "$file" | head -20
            echo ""
        fi
    done
    
    if [ "$INCLUDE_STDERR" = true ] && [ -n "$STDERR_FILES" ]; then
        for file in $STDERR_FILES; do
            if [ -f "$file" ]; then
                echo -e "\033[35m=== Workflow $WORKFLOW_ID in $(basename $file) ===\033[0m"
                grep -n "$WORKFLOW_ID" "$file" | head -20
                echo ""
            fi
        done
    fi
elif [[ "$FILTER" == record_id=* ]]; then
    # Filter by record_id
    RECORD_ID="${FILTER#record_id=}"
    for file in $FILES; do
        if [ -f "$file" ]; then
            echo -e "\033[36m=== Record $RECORD_ID in $(basename $file) ===\033[0m"
            grep -n "$RECORD_ID" "$file" | head -20
            echo ""
        fi
    done
    
    if [ "$INCLUDE_STDERR" = true ] && [ -n "$STDERR_FILES" ]; then
        for file in $STDERR_FILES; do
            if [ -f "$file" ]; then
                echo -e "\033[35m=== Record $RECORD_ID in $(basename $file) ===\033[0m"
                grep -n "$RECORD_ID" "$file" | head -20
                echo ""
            fi
        done
    fi
else
    echo "❌ Unknown filter: $FILTER"
    exit 1
fi
