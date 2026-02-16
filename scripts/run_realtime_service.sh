#!/bin/bash
# scripts/run_realtime_service.sh

# Path Guard
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Pick Python
PY="${PY:-./.venv/bin/python}"
if [ ! -x "$PY" ]; then
    PY="python3"
fi

export PYTHONPATH="$REPO_ROOT/src"
export REALTIME_SYMBOLS="${REALTIME_SYMBOLS:-BTCUSDT,ETHUSDT,BNBUSDT}"
# Indefinite run: set high duration or change run_ws.py to allow -1 (0 means default 30 in current config)
# Actually, looking at run_ws.py, it uses REALTIME_RUN_SECONDS from config (default 30).
# We'll set it to a very large number for service mode.
export REALTIME_RUN_SECONDS=86400

LOG_FILE="logs/realtime_ws.log"
mkdir -p logs

echo "--- Starting Realtime Service ($(date)) ---" | tee -a "$LOG_FILE"

delay=2
max_delay=60

while true; do
    echo "Launching run_ws.py..." >> "$LOG_FILE"
    
    # Run the script. Capturing PID for cleanup if needed.
    "$PY" scripts/run_ws.py >> "$LOG_FILE" 2>&1
    
    exit_code=$?
    echo "run_ws.py exited with code $exit_code. Restarting in ${delay}s..." >> "$LOG_FILE"
    
    # Simple Exponential Backoff
    sleep $delay
    if [ $exit_code -eq 0 ]; then
        delay=2 # Reset on clean exit
    else
        delay=$((delay * 2))
        if [ $delay -gt $max_delay ]; then
            delay=$max_delay
        fi
    fi
done
