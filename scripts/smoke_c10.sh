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

# Run Bridge directly (it launches C7+C8+Bridge)
# Run for 20 seconds
python scripts/run_bridge.py --seconds 20 --mode B

echo "--- Checking Output Files ---"
ls -l data/state/execution_*.jsonl || echo "No execution files found (maybe no signals)"
ls -l data/signals/$(date +%Y-%m-%d)/signals.jsonl || echo "No signal file found"

echo "--- Smoke Test Complete ---"
