#!/bin/bash
# scripts/daily_etl.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Pick Python
PY="${PY:-./.venv/bin/python}"
if [ ! -x "$PY" ]; then
    PY="python3"
fi

SYMBOLS="BTCUSDT ETHUSDT BNBUSDT"
START_DATE=$(date -u -v-3d +"%Y-%m-%d") # 3 days ago for safety

echo "--- Daily ETL Started ($(date)) ---"
echo "Fetching from $START_DATE to now"

for sym in $SYMBOLS; do
    echo ">> Processing $sym"
    
    # 1. Ingest (Supports --start --end)
    "$PY" scripts/ingest_historical.py --symbol "$sym" --start "$START_DATE" --end "now"
    
    # 2. Aggregate (Standard TFs)
    "$PY" scripts/aggregate_data.py --symbol "$sym"
done

echo "--- Daily ETL Complete ($(date)) ---"
