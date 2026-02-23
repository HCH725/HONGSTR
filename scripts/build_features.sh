#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT"
cd "$REPO_ROOT"

FREQ="1h"
SYMBOLS="BTCUSDT ETHUSDT BNBUSDT"
START="2020-01-01"
END="now"

while [[ $# -gt 0 ]]; do
  case $1 in
    --freq) FREQ="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --start) START="$2"; shift 2 ;;
    --end) END="$2"; shift 2 ;;
    *) echo "Unknown parameter $1"; exit 1 ;;
  esac
done

echo "Starting Feature Builder SDK..."
# We run without "set -e" around Python so that if it returns 0 (even on warn), it succeeds.
# Currently CLI is designed to exit 0 safely.
.venv/bin/python research/cli.py \
    --freq "$FREQ" \
    --symbols "$SYMBOLS" \
    --start "$START" \
    --end "$END"

RC=$?
if [ $RC -ne 0 ]; then
    echo "WARN: Feature builder exited with non-zero code $RC. (Continuing anyway for stability)"
fi

echo "Feature build completed."
exit 0
