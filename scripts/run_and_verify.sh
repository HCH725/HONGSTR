#!/bin/bash
set -euo pipefail

# Deterministic Backtest Runner & Verifier
# Usage: ./scripts/run_and_verify.sh [--mode foreground|background] [args for run_backtest.py]

MODE="foreground"
PASSTHROUGH_ARGS=()

while [[ $# -gt 0 ]]; do
  case $1 in
    --mode)
      MODE="$2"
      shift 2
      ;;
    *)
      PASSTHROUGH_ARGS+=("$1")
      shift
      ;;
  esac
done

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
# Add random suffix to ensure uniqueness even if called rapidly
RAND=$(echo $RANDOM | md5sum | head -c 4 || echo "0000") 
RUN_ID="${TIMESTAMP}_${RAND}"

# Deterministic Output Directory
REPO_ROOT=$(pwd)
DATE_STR=$(date -u +%Y-%m-%d)
OUT_DIR="${REPO_ROOT}/data/backtests/${DATE_STR}/${RUN_ID}"
LOG_DIR="${REPO_ROOT}/logs"
LOG_FILE="${LOG_DIR}/backtest_${RUN_ID}.log"

mkdir -p "$LOG_DIR" "$OUT_DIR"

echo "=== HONGSTR Backtest Runner ==="
echo "RUN_ID:  $RUN_ID"
echo "OUT_DIR: $OUT_DIR"
echo "MODE:    $MODE"
echo "LOG:     $LOG_FILE"

# Prepare Python Command
# We explicitly pass --out_dir to enforce deterministic output
CMD=(
  "./.venv/bin/python" "-u" "scripts/run_backtest.py"
  "--out_dir" "$OUT_DIR"
  "--run_id" "$RUN_ID"
  "${PASSTHROUGH_ARGS[@]}"
)

if [ "$MODE" == "background" ]; then
  echo "Starting backtest in background..."
  "${CMD[@]}" > "$LOG_FILE" 2>&1 &
  PID=$!
  echo "PID: $PID"
  
  # Polling Loop
  echo "Waiting for summary.json in $OUT_DIR (timeout 20m)..."
  START_TIME=$SECONDS
  TIMEOUT=$((20 * 60))
  
  while true; do
    if [ -f "${OUT_DIR}/summary.json" ]; then
      echo "Success: summary.json found."
      break
    fi
    
    # Check if process died
    if ! kill -0 $PID 2>/dev/null; then
       echo "Error: Backtest process $PID died without creating summary.json."
       echo "Tail of log:"
       tail -n 10 "$LOG_FILE"
       exit 1
    fi
    
    ELAPSED=$(($SECONDS - $START_TIME))
    if [ $ELAPSED -gt $TIMEOUT ]; then
      echo "Error: Timeout waiting for summary.json."
      exit 1
    fi
    
    sleep 5
  done
  
else
  # Foreground
  echo "Starting backtest in foreground..."
  # Use tee to show output and save to log
  "${CMD[@]}" 2>&1 | tee "$LOG_FILE"
  
  if [ ! -f "${OUT_DIR}/summary.json" ]; then
    echo "Error: summary.json not found in $OUT_DIR after execution."
    exit 1
  fi
fi

# Generate Optimizer Artifact (Stub)
echo "--- Generating Optimizer Artifact ---"
./.venv/bin/python scripts/generate_optimizer_artifact.py --dir "$OUT_DIR"

# Generate Regime Report
echo "--- Generating Regime Report ---"
./.venv/bin/python scripts/generate_regime_report.py --dir "$OUT_DIR"

# Generate Regime Gate
echo "--- Generating Regime Gate Artifact ---"
G_SYMS="BTCUSDT,ETHUSDT,BNBUSDT"
G_MODE="SHORT"
for i in "${!PASSTHROUGH_ARGS[@]}"; do
  if [[ "${PASSTHROUGH_ARGS[$i]}" == "--symbols" ]]; then
    G_SYMS="${PASSTHROUGH_ARGS[$((i+1))]}"
  fi
  # If any passthrough arg contains 'FULL', assume FULL mode for gate
  if [[ "${PASSTHROUGH_ARGS[$i]}" == *"FULL"* ]]; then
    G_MODE="FULL"
  fi
done
./.venv/bin/python scripts/generate_gate_artifact.py --dir "$OUT_DIR" --mode "$G_MODE" --symbols "$G_SYMS" --timeframe 4h

# Generate Regime-Aware Optimization
echo "--- Generating Regime-Aware Optimization Artifact ---"
./.venv/bin/python scripts/generate_optimizer_regime_artifact.py --run_dir "$OUT_DIR" --topk 5

# Generate Regime-Driven Selection
echo "--- Generating Regime-Driven Selection Artifact ---"
./.venv/bin/python scripts/generate_selection_artifact.py --run_dir "$OUT_DIR" --topk 5 --respect_gate true

# Verify
echo "--- Verifying Results ---"
# Reuse GATE_SYMS logic or extraction above, but we have not extracted it for verify yet.
# Let's extract symbols for verify specifically or reuse the extraction logic.
# Actually, we can move the extraction logic up or duplicate it.
# Let's verify with the same symbols passed to run_backtest.py if available.

VERIFY_SYMS="BTCUSDT,ETHUSDT,BNBUSDT" # Default
for i in "${!PASSTHROUGH_ARGS[@]}"; do
  if [[ "${PASSTHROUGH_ARGS[$i]}" == "--symbols" ]]; then
    VERIFY_SYMS="${PASSTHROUGH_ARGS[$((i+1))]}"
  fi
done

./.venv/bin/python scripts/verify_latest.py --dir "$OUT_DIR" --symbols "$VERIFY_SYMS"

# Gate
echo "--- Checking Quality Gate ---"
# Attempt to find symbols in passthrough args, fallback to default
GATE_SYMS="BTCUSDT,ETHUSDT,BNBUSDT"
for i in "${!PASSTHROUGH_ARGS[@]}"; do
  if [[ "${PASSTHROUGH_ARGS[$i]}" == "--symbols" ]]; then
    GATE_SYMS="${PASSTHROUGH_ARGS[$((i+1))]}"
  fi
done

if ! ./.venv/bin/python scripts/gate_summary.py --dir "$OUT_DIR" --timeframes 1h,4h --symbols "$GATE_SYMS"; then
    echo "Backtest failed quality gate."
    echo "--- Generating Action Items ---"
    ./.venv/bin/python scripts/generate_action_items.py --data_dir "data"
    exit 2
fi

echo "--- Generating Action Items ---"
./.venv/bin/python scripts/generate_action_items.py --data_dir "data"

echo "Done."
