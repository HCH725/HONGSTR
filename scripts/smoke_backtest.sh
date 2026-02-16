#!/bin/bash
export PYTHONPATH=src
export STRATEGY_TIMEFRAME_SIGNAL=1m

echo "--- Preparing Smoke Environment ---"
SMOKE_ROOT="tmp/smoke_data"
rm -rf "$SMOKE_ROOT"
mkdir -p "$SMOKE_ROOT/BTCUSDT/1m"
cp tests/fixtures/klines_1m_sample.jsonl "$SMOKE_ROOT/BTCUSDT/1m/klines.jsonl"

echo "--- Running Backtest Runner (Smoke) ---"
# We use 1m timeframe because our fixture is short.
python scripts/run_backtest.py \
    --symbols "BTCUSDT" \
    --timeframes "1m" \
    --data_root "$SMOKE_ROOT" \
    --out_root "tmp/backtests_smoke" \
    --strategy "vwap_supertrend" \
    --size_notional_usd 1000

# Identify the run folder
RUN_DATE=$(date -u +"%Y-%m-%d")
RUN_DIR=$(ls -td tmp/backtests_smoke/$RUN_DATE/*/ | head -1)

if [ -z "$RUN_DIR" ]; then
    echo "FAILURE: Run directory not created."
    exit 1
fi

echo "Verifying Outputs in $RUN_DIR..."

# 1. Check summary.json
if [ ! -f "$RUN_DIR/summary.json" ]; then
    echo "FAILURE: summary.json missing."
    exit 1
fi

# Assert keys in summary.json (using simple grep to avoid dependencies)
for key in "total_return" "sharpe" "max_drawdown" "trades_count" "win_rate" "avg_trade_return" "exposure_time" "start_ts" "end_ts"; do
    grep -q "$key" "$RUN_DIR/summary.json" || { echo "FAILURE: Key $key missing in summary.json"; exit 1; }
done

# 2. Check equity_curve.jsonl line count
EQUITY_COUNT=$(wc -l < "$RUN_DIR/equity_curve.jsonl")
if [ "$EQUITY_COUNT" -lt 10 ]; then
    echo "FAILURE: equity_curve.jsonl too short ($EQUITY_COUNT lines)."
    exit 1
fi

# 3. Check trades.jsonl
if [ ! -f "$RUN_DIR/trades.jsonl" ]; then
    echo "FAILURE: trades.jsonl missing."
    exit 1
fi

# Our fixture is a continuous uptrend, so it should trigger a LONG entry early.
TRADE_COUNT=$(wc -l < "$RUN_DIR/trades.jsonl")
if [ "$TRADE_COUNT" -lt 1 ]; then
    echo "FAILURE: No trades executed in smoke test."
    # If this fails, we might need a better fixture or verify strategy triggers on 1m.
    # vwap_supertrend uses ATR(10). 25 bars is plenty.
    exit 1
fi

echo "SUCCESS: Backtest Smoke Passed."
echo "Folder: $RUN_DIR"
