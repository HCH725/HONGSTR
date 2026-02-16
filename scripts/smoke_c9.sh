#!/bin/bash
set -e

# Validate C9 Strategy Engine (Mock Run)
echo "Starting C9 Strategy Engine Smoke Test..."
echo "Duration: 45s"

# Ensure env vars
export STRATEGY_ENABLED=true
export REALTIME_SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"

# Source venv if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run the python script
python3 scripts/run_signal_strategies.py --seconds 45

# Check outputs
echo "Checking outputs..."
ls -R data/signals

# Find latest signals file
LATEST_SIG=$(find data/signals -name "signals.jsonl" | sort | tail -n 1)

if [ -f "$LATEST_SIG" ]; then
    echo "Latest Signals File: $LATEST_SIG"
    echo "--- Head ---"
    head -n 2 "$LATEST_SIG"
    echo "--- Tail ---"
    tail -n 2 "$LATEST_SIG"
else
    echo "No signals.jsonl found (might be expected if no signals triggered in 45s)"
fi

echo "--- Smoke Test Complete ---"
