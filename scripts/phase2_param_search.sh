#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Phase 2 Pre-check: Data Coverage ==="
set +e
bash scripts/check_data_coverage.sh > /tmp/hongstr_phase2_cov.log 2>&1
RC=$?
set -e

if [ "$RC" -ne 0 ]; then
  echo "ERROR: Data coverage NOT PASS. Please fix before running Phase 2." >&2
  cat /tmp/hongstr_phase2_cov.log
  exit 2
fi

echo "Coverage PASS. Starting Parameter Sweep..."

PY="${REPO_ROOT}/.venv/bin/python"

SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"
TIMEFRAMES="1h,4h"
IS_START="2020-01-01"
IS_END=$(python3 -c "from scripts.splits import IS_END_DATE; print(IS_END_DATE)")
OOS_START=$(python3 -c "from scripts.splits import OOS_START_DATE; print(OOS_START_DATE)")
OOS_END="now"

ATR_PERIODS=(10 14)
ATR_MULTS=(2.5 3.0)

PHASE2_DIR="reports/strategy_research/phase2"
mkdir -p "$PHASE2_DIR"
INDEX_FILE="${PHASE2_DIR}/run_index.tsv"

echo -e "run_dir\tphase\tatr_period\tatr_mult\tstart\tend" > "$INDEX_FILE"

run_experiment() {
  local phase="$1"
  local start="$2"
  local end="$3"
  local period="$4"
  local mult="$5"
  
  local json="{\"atr_period\":$period,\"atr_mult\":$mult}"
  
  # Run Backtest
  set +e
  OUT_LOG="$( "$PY" scripts/run_backtest.py \
    --symbols "$SYMBOLS" \
    --timeframes "$TIMEFRAMES" \
    --start "$start" \
    --end "$end" \
    --params-json "$json" 2>&1 )"
  local rc=$?
  set -e
  
  if [ "$rc" -ne 0 ]; then
    echo "ERROR: Backtest failed for $phase params=$json"
    echo "$OUT_LOG"
    return 1
  fi
  
  local run_dir="$(echo "$OUT_LOG" | awk -F= '/COMPLETED_DIR=/{print $2}')"
  if [ -z "$run_dir" ]; then
    echo "ERROR: Could not find COMPLETED_DIR in output for $phase params=$json"
    return 1
  fi
  
  echo -e "${run_dir}\t${phase}\t${period}\t${mult}\t${start}\t${end}" >> "$INDEX_FILE"
  echo "Finished $phase $period $mult -> $run_dir"
}

total=$((${#ATR_PERIODS[@]} * ${#ATR_MULTS[@]} * 2))
current=0

for p in "${ATR_PERIODS[@]}"; do
  for m in "${ATR_MULTS[@]}"; do
    # IS Phase
    current=$((current+1))
    echo "[$current/$total] Running IS: atr_period=$p atr_mult=$m"
    run_experiment "IS" "$IS_START" "$IS_END" "$p" "$m"
    
    # OOS Phase
    current=$((current+1))
    echo "[$current/$total] Running OOS: atr_period=$p atr_mult=$m"
    run_experiment "OOS" "$OOS_START" "$OOS_END" "$p" "$m"
  done
done

echo "=== Parameter Sweep Finished ==="
echo "Generating Reports..."
"$PY" scripts/report_phase2.py --index "$INDEX_FILE" --out_dir "$PHASE2_DIR"
echo "Phase 2 Pipeline Complete. Results in $PHASE2_DIR"
