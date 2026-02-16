#!/bin/bash
# scripts/watch_realtime.sh

set -euo pipefail

# Default values
DATE=$(date -u +"%Y-%m-%d")
SYMBOL="BTCUSDT"
LINES=20

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --date) DATE="$2"; shift ;;
        --symbol) SYMBOL="$2"; shift ;;
        --lines) LINES="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== HONGSTR Realtime Watcher ($DATE) ==="

# 1. Check Log
echo -e "\n--- logs/realtime_ws.log (last $LINES lines) ---"
if [ -f "logs/realtime_ws.log" ]; then
    tail -n "$LINES" "logs/realtime_ws.log"
else
    echo "Log file logs/realtime_ws.log not found."
fi

# 2. Check Data Files
DIR="data/realtime/$DATE"
echo -e "\n--- Data Directory: $DIR ---"
if [ -d "$DIR" ]; then
    ls -lt "$DIR" | head -n 10
    
    # Tail kline file for the symbol
    KLINE_FILE="$DIR/kline_${SYMBOL}_1m.jsonl"
    if [ -f "$KLINE_FILE" ]; then
        echo -e "\n--- $KLINE_FILE (last 5 lines) ---"
        tail -n 5 "$KLINE_FILE"
    else
        echo -e "\n$KLINE_FILE not found."
    fi
else
    echo "Directory $DIR not found. WS might not have started or written files yet."
fi
