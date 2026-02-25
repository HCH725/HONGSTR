#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Phase 3 Pre-check: Data Coverage ==="
set +e
bash scripts/check_data_coverage.sh > /tmp/hongstr_phase3_cov.log 2>&1
RC=$?
set -e

if [ "$RC" -ne 0 ]; then
  echo "ERROR: Data coverage NOT PASS. Please fix before running Phase 3." >&2
  cat /tmp/hongstr_phase3_cov.log
  exit 2
fi
echo "Coverage PASS. Starting Parameter Sweep..."

PY="${REPO_ROOT}/.venv/bin/python"
SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"
TIMEFRAMES="1h,4h"

PHASE2_JSON="reports/strategy_research/phase2/phase2_results.json"
if [ ! -f "$PHASE2_JSON" ]; then
    echo "ERROR: $PHASE2_JSON not found."
    exit 1
fi

CANDIDATES=$("$PY" -c '
import json, sys
try:
    with open("'$PHASE2_JSON'") as f:
        data = json.load(f)
        for c in data.get("oos_candidates", []):
            print("{}:{}".format(c["atr_period"], c["atr_mult"]))
except Exception as e:
    sys.exit(1)
')

PHASE3_DIR="reports/strategy_research/phase3"
mkdir -p "$PHASE3_DIR"
INDEX_FILE="${PHASE3_DIR}/run_index.tsv"

# Clear index file
echo -e "timestamp\tsplit_name\tphase\tatr_period\tatr_mult\tstart\tend\trun_dir\trc" > "$INDEX_FILE"

run_experiment() {
  local split_name="$1"
  local phase="$2"
  local start="$3"
  local end="$4"
  local period="$5"
  local mult="$6"
  
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
  
  local ts=$(date +%s)
  local run_dir="$(echo "$OUT_LOG" | awk -F= '/COMPLETED_DIR=/{print $2}')"
  if [ -z "$run_dir" ]; then
    run_dir="ERROR"
  fi
  
  echo -e "${ts}\t${split_name}\t${phase}\t${period}\t${mult}\t${start}\t${end}\t${run_dir}\t${rc}" >> "$INDEX_FILE"
  echo "Finished $split_name $phase $period $mult -> $run_dir (RC: $rc)"
}

# The defined splits:
# Fixed:
# IS: 2020-01-01 -> 2023-12-31 | OOS: 2024-01-01 -> now
# WF1:
# IS: 2020-01-01 -> 2022-12-31 | OOS: 2023-01-01 -> 2023-12-31
# WF2:
# IS: 2020-01-01 -> 2023-12-31 | OOS: 2024-01-01 -> 2024-12-31
# WF3:
# IS: 2020-01-01 -> 2024-12-31 | OOS: 2025-01-01 -> now

SPLITS=(
    "FIXED|2020-01-01|2023-12-31|2024-01-01|now"
    "WF1|2020-01-01|2022-12-31|2023-01-01|2023-12-31"
    "WF2|2020-01-01|2023-12-31|2024-01-01|2024-12-31"
    "WF3|2020-01-01|2024-12-31|2025-01-01|now"
)

for cand in $CANDIDATES; do
    p=$(echo "$cand" | cut -d: -f1)
    m=$(echo "$cand" | cut -d: -f2)
    
    for spl in "${SPLITS[@]}"; do
        split_name=$(echo "$spl" | cut -d\| -f1)
        is_st=$(echo "$spl" | cut -d\| -f2)
        is_ed=$(echo "$spl" | cut -d\| -f3)
        oos_st=$(echo "$spl" | cut -d\| -f4)
        oos_ed=$(echo "$spl" | cut -d\| -f5)
        
        echo "Running $split_name IS for period $p mult $m"
        run_experiment "$split_name" "IS" "$is_st" "$is_ed" "$p" "$m"
        
        echo "Running $split_name OOS for period $p mult $m"
        run_experiment "$split_name" "OOS" "$oos_st" "$oos_ed" "$p" "$m"
    done
done

echo "=== Phase 3 Parameter Sweep Finished ==="
echo "Generating Reports..."
"$PY" scripts/report_phase3.py --index "$INDEX_FILE" --out_dir "$PHASE3_DIR"
echo "Phase 3 Pipeline Complete. Results in $PHASE3_DIR"
