#!/bin/bash
set -euo pipefail

# Deterministic Backtest Runner & Verifier
# Usage: ./scripts/run_and_verify.sh [optional extra args for run_backtest.py]

# 1. Setup deterministic output
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/backtest_${TIMESTAMP}.log"
mkdir -p logs

echo "Starting Deterministic Backtest Run: $TIMESTAMP"
echo "Log: $LOG_FILE"

# 2. Run Backtest
# We use -u for unbuffered output to see logs in real-time
set +e
./.venv/bin/python -u scripts/run_backtest.py \
  --run_id "$TIMESTAMP" \
  "$@" 2>&1 | tee "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

if [ $EXIT_CODE -ne 0 ]; then
    echo "Backtest failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi

# 3. Read Captured Directory from Log
# More robust: grep last occurrence
COMPLETED_DIR=$(grep "^COMPLETED_DIR=" "$LOG_FILE" | tail -n 1 | cut -d= -f2 | tr -d '\r')

if [ -z "$COMPLETED_DIR" ]; then
    echo "Error: Could not determine COMPLETED_DIR from output."
    echo "Check logs: $LOG_FILE"
    exit 1
fi

echo "Backtest completed at: $COMPLETED_DIR"

# 4. Verify
echo "--- Verifying ---"
./.venv/bin/python scripts/verify_latest.py --dir "$COMPLETED_DIR"

echo "Done."
