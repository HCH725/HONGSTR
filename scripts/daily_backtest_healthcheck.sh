#!/bin/bash
# scripts/daily_backtest_healthcheck.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Pick Python
PY="${PY:-./.venv/bin/python}"
if [ ! -x "$PY" ]; then
    PY="python3"
fi

echo "--- Daily Backtest Healthcheck ($(date)) ---"

# 1. Smoke Test (Fixture based)
echo "Running smoke_backtest.sh..."
bash scripts/smoke_backtest.sh

# 2. Quick Real-Data Backtest (Recent 14 days)
# Calculate dates for 14 day window
START_DT=$(date -u -v-14d +"%Y-%m-%d")
END_DT="now"

echo "Running 14-day Backtest ($START_DT to $END_DT) for BTCUSDT..."
# Check if data exists first
if [ ! -d "data/derived/BTCUSDT/1h" ]; then
    echo "ERROR: Missing derived data for BTCUSDT. Run daily_etl.sh first."
    exit 1
fi

"$PY" scripts/run_backtest.py \
    --symbols "BTCUSDT" \
    --timeframes "1h,4h" \
    --strategy "vwap_supertrend" \
    --start "$START_DT" \
    --end "$END_DT" \
    --size_notional_usd 1000 \
    --fee_bps 4 \
    --slippage_bps 2

# 3. Log to CSV
LATEST_DIR="$(ls -1dt data/backtests/*/* | head -n 1 || true)"
REPORT_FILE="data/reports/daily_backtest_health.csv"
mkdir -p data/reports

if [ ! -f "$REPORT_FILE" ]; then
    echo "ts,status,total_return,trades_count,max_drawdown,sharpe" > "$REPORT_FILE"
fi

if [ -f "$LATEST_DIR/summary.json" ]; then
    # Extract metrics using python (safe & no dependencies like jq required)
    METRICS=$("$PY" -c "import json; s=json.load(open('$LATEST_DIR/summary.json')); print(f\"{s.get('total_return',0)},{s.get('trades_count',0)},{s.get('max_drawdown',0)},{s.get('sharpe',0)}\")")
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ"),SUCCESS,$METRICS" >> "$REPORT_FILE"
    echo "Healthcheck Passed."
else
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ"),FAILURE,0,0,0,0" >> "$REPORT_FILE"
    echo "Healthcheck Failed: summary.json missing."
    exit 1
fi
