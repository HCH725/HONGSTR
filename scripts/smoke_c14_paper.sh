#!/bin/bash
export PYTHONPATH=src
export EXECUTION_MODE=B
export PORTFOLIO_ID=HONG

# Pick python
PY="${PY:-./.venv/bin/python}"
if [ ! -x "$PY" ]; then
    PY="python3"
fi

echo "Using PY=$PY"

# 1. Unit Tests (Minimal subset)
echo "Running Unit Tests..."
"$PY" -m pytest -q tests/test_bridge.py tests/test_signal_engine_io.py tests/test_signal_resample.py tests/test_realtime_ws.py tests/test_risk_manager.py
if [ $? -ne 0 ]; then
    echo "Unit Tests Failed."
    exit 1
fi

# 2. Ops Runner (End-to-End)
# Clean state to ensure verification counts new lines
rm -f data/state/execution_result.jsonl
# Also need to ensure Valid Selection for Helper Injector to work?
# The runner attempts to read selection.
# Let's ensure a dummy selection exists for this smoke test to be robust.
mkdir -p data/selection
cat > data/selection/hong_selected.json <<EOF
{
  "schema_version": "selection_artifact_v1",
  "portfolio_id": "HONG",
  "timestamp_gmt8": "2026-02-17T00:00:00+08:00",
  "selection": {
     "BULL": ["test_strategy", "vwap_supertrend"],
     "BEAR": [],
     "NEUTRAL": []
  },
  "policy": {},
  "metadata": {"git_commit": "smoke"}
}
EOF

echo "Running All-in-One Runner (20s)..."
# Using dry run / paper mode
"$PY" scripts/run_all_paper.py --seconds 20

# 3. Verify
if [ -f data/state/execution_result.jsonl ]; then
    count=$(wc -l < data/state/execution_result.jsonl)
    if [ "$count" -ge 1 ]; then
        echo "SUCCESS: Execution Result created with $count lines."
    else
        echo "FAILURE: Execution Result empty."
        exit 1
    fi
else
    echo "FAILURE: Execution Result file missing."
    exit 1
fi
