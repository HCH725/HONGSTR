#!/bin/bash
set -e

# Run C7 smoke for 30s in background
echo "Starting C7 (realtime feed) for 30s..."
python scripts/run_ws.py --duration 30 &
C7_PID=$!

# Wait a bit for C7 to start and create files
sleep 5

# Run C8 (signal engine) for 20s
echo "Starting C8 (signal engine) for 20s..."
python scripts/run_signal_engine.py --duration 20

# Wait for C7
wait $C7_PID

echo "Checking outputs..."
ls -l data/signals
ls -l data/state
