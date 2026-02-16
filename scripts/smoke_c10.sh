#!/bin/bash
set -e

# Activate venv
source .venv/bin/activate

# Setup Env
export EXECUTION_MODE="B" # Paper
export OFFLINE_MODE="0"
export SIGNAL_ENABLED="1"
export REALTIME_SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"

echo "Starting C10 Execution Bridge Smoke Test..."

# 0. Clean State (Paper Broker Persistence)
rm -f data/paper/positions.json
rm -f data/state/execution_*.jsonl

# 1. Inject Deterministic Signal
echo "Injecting Signal..."
python scripts/inject_one_signal.py

# 2. Run Bridge (C7+C8+Bridge)
# Run for 15 seconds to allow processing
echo "Running Bridge..."
python scripts/run_bridge.py --seconds 15 --mode B

echo "--- Checking Output Files ---"
# 3. Verify Execution
EXEC_FILES=$(ls data/state/execution_*.jsonl 2>/dev/null || true)

if [ -z "$EXEC_FILES" ]; then
    echo "FAIL: No execution files found in data/state"
    ls -lah data/state
    exit 1
fi

COUNT=$(cat data/state/execution_*.jsonl | wc -l)
if [ "$COUNT" -ge 1 ]; then
    echo "PASS: Found $COUNT execution records."
    tail -n 3 data/state/execution_*.jsonl
else
    echo "FAIL: Execution files exist but are empty."
    exit 1
fi

echo "--- Smoke Test Complete ---"
