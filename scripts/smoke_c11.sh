#!/bin/bash
set -e

# Activate venv
source .venv/bin/activate
export PYTHONPATH=src

# Setup Env (Scenario 1: Allow)
echo "----- SCENARIO 1: ALLOW (Loose Limits) -----"
# Reset state
rm -f data/paper/positions.json
rm -f data/state/execution_*.jsonl
# Inject
python scripts/inject_one_signal.py
# Run Bridge (Allow)
# Default limits are loose (5k order, 50k total)
# Signal is for 0.1 BTC @ 100k (fallback) -> 10k notional?
# Wait, Executor fallback price is 100,000.
# Config POSITION_SIZE_PCT_DEFAULT=0.1. Balance=100k.
# Size = 10k. Qty = 0.1.
# Notional = 10k.
# MAX_ORDER_NOTIONAL in config default is 5000.
# So default limits MIGHT REJECT 10k order!
# I should set MAX_ORDER_NOTIONAL=20000 for ALLOW scenario.
export MAX_ORDER_NOTIONAL=20000
export MAX_TOTAL_EXPOSURE=100000
export ALLOW_LONG=true
export ALLOW_SHORT=true

# Run bridge for 15s
python scripts/run_bridge.py --seconds 15

# Verify ALLOW
if grep -q '"decision": "ALLOWED"' data/state/execution_result.jsonl; then
    echo "PASS: Scenario 1 execution ALLOWED."
else
    echo "FAIL: Scenario 1 execution NOT Allowed."
    cat data/state/execution_result.jsonl
    exit 1
fi

# Setup Env (Scenario 2: Reject)
echo "----- SCENARIO 2: REJECT (Strict Limits) -----"
# Reset state? 
# If I reset, I lose previous result log.
# I want to append or verify new log.
# Bridge appends to jsonl.
# Inject another signal?
# inject_one_signal.py uses fixed ID/Timestamp?
# If ID is same, idempotency might block it?
# scripts/inject_one_signal.py:
# "ts": pd.Timestamp.now(tz="UTC")
# So TS is new.
# "strategy_id": "smoke_test_injector".
# Executor handles idempotency? it checks open orders/positions.
# Scenario 1 placed a position.
# Scenario 2: If I inject same symbol "BTCUSDT", Position exists (LONG).
# Signal defaults to LONG.
# Executor logic: "Same side position, ignoring."
# So Scenario 2 might be ignored due to logic, not Risk Manager!
# I need to clear paper position for Scenario 2 execution to attempt open.
rm -f data/paper/positions.json

# Inject new signal
python scripts/inject_one_signal.py

# Strict Limits
export MAX_ORDER_NOTIONAL=1 # 1 USD limit
# Run bridge
python scripts/run_bridge.py --seconds 15

# Verify REJECT
if grep -q '"status": "REJECTED_RISK"' data/state/execution_result.jsonl; then
    echo "PASS: Scenario 2 execution REJECTED."
else
    echo "FAIL: Scenario 2 execution NOT Rejected."
    cat data/state/execution_result.jsonl
    exit 1
fi

echo "--- C11 Smoke Test Complete ---"
