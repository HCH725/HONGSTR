#!/bin/bash
export PYTHONPATH=src
export OFFLINE_MODE=true
export EXECUTION_MODE=B
export PORTFOLIO_ID=test_portfolio

# Clean state
rm -rf data/state
rm -rf data/selection
rm -rf data/signals
mkdir -p data/state
mkdir -p data/selection

# Create valid selection artifact
# Path: data/selection/hong_selected.json (Default)
SELECTION_FILE="data/selection/hong_selected.json"
cat > $SELECTION_FILE <<EOF
{
  "schema_version": "selection_artifact_v1",
  "portfolio_id": "test_portfolio",
  "timestamp_gmt8": "2026-02-17T00:00:00+08:00",
  "selection": {
     "BULL": ["test_strategy"],
     "BEAR": ["test_strategy"],
     "NEUTRAL": []
  },
  "policy": {
      "neutral_policy": "NO_TRADE"
  },
  "metadata": {"git_commit": "test"}
}
EOF

# Signals Path
DATE_STR=$(date -u +"%Y-%m-%d")
SIGNALS_DIR="data/signals/$DATE_STR"
mkdir -p "$SIGNALS_DIR"

# Inject 1 signal line (Valid Schema matched to selection)
echo '{"ts": "'$(date -u +"%Y-%m-%dT%H:%M:%S")'", "symbol": "BTCUSDT", "portfolio_id": "test_portfolio", "strategy_id": "test_strategy", "direction": "LONG", "timeframe": "1m", "regime": "TREND", "confidence": 1.0}' > "$SIGNALS_DIR/signals.jsonl"

# Run Bridge (Only Bridge)
echo "Running Bridge..."
python -c "import asyncio, os, logging; logging.getLogger('src.hongstr').setLevel(logging.INFO); from hongstr.bridge.signal_to_execution import SignalExecutionBridge; asyncio.run(SignalExecutionBridge().run(duration=5))"

# Verify
if [ -f data/state/execution_result.jsonl ]; then
    count=$(wc -l < data/state/execution_result.jsonl)
    if [ "$count" -ge 1 ]; then
        echo "SUCCESS: Execution Result created with $count lines."
        cat data/state/execution_result.jsonl
    else
        echo "FAILURE: Execution Result empty."
        exit 1
    fi
else
    echo "FAILURE: Execution Result file missing."
    ls -R data/state
    exit 1
fi
