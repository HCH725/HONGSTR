#!/bin/bash
set -euo pipefail

# ===== HONGSTR Benchmark Suite =====
# Based on user request, with added safety checks.

# locate repo root
REPO="$(pwd -P)"
while [[ "$REPO" != "/" && ! -f "$REPO/pyproject.toml" ]]; do REPO="$(dirname "$REPO")"; done
[[ -f "$REPO/pyproject.toml" ]] || { echo "ERROR: cannot find repo root (pyproject.toml)"; exit 1; }
cd "$REPO"
echo "REPO=$REPO"

PY="./.venv/bin/python"
[[ -x "$PY" ]] || { echo "ERROR: ./.venv/bin/python not found"; exit 1; }

SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"
TFS="1h,4h"
STRATEGY="vwap_supertrend"
FEE_BPS="4"
SLIP_BPS="2"
SIZE_USD="1000"

mkdir -p logs

# ===== helper to run backtest + verify =====
run_bt () {
  local TAG="$1"
  local START="$2"
  local END="$3"

  echo
  echo "=== RUN ${TAG} (Pipeline) ==="
  echo "start=$START end=$END"
  
  # Call run_and_verify.sh
  # It will print RUN_ID and OUT_DIR
  # We capture the output to find OUT_DIR
  # We allow exit code 2 (Gate failure) to continue so we can report it
  local PIPE_OUT
  set +e
  PIPE_OUT=$(bash scripts/run_and_verify.sh \
    --mode foreground \
    --symbols "$SYMBOLS" \
    --timeframes "$TFS" \
    --strategy "$STRATEGY" \
    --start "$START" \
    --end "$END" \
    --size_notional_usd "$SIZE_USD" \
    --fee_bps "$FEE_BPS" \
    --slippage_bps "$SLIP_BPS" 2>&1 | tee /dev/tty)
  local EXIT_CODE=$?
  set -e

  if [[ $EXIT_CODE -ne 0 && $EXIT_CODE -ne 2 ]]; then
    echo "ERROR: Pipeline failed for ${TAG} with exit code ${EXIT_CODE}"
    exit 1
  fi

  # Extract OUT_DIR from output
  local RUN_OUT_DIR
  RUN_OUT_DIR=$(echo "$PIPE_OUT" | grep "OUT_DIR:" | awk '{print $2}' | tr -d '\r')
  
  if [[ -z "$RUN_OUT_DIR" || ! -d "$RUN_OUT_DIR" ]]; then
    echo "ERROR: Could not determine OUT_DIR for ${TAG}"
    exit 1
  fi

  echo "COMPLETED ${TAG} => ${RUN_OUT_DIR}"
  eval "OUT_DIR_${TAG}=\"${RUN_OUT_DIR}\""
}

# ===== date ranges =====
NOW_UTC="$(date -u +%Y-%m-%d)"
# CLI Overrides (Simple parsing)
START_FULL_VAL="2020-01-01"
START_SHORT_VAL="$(date -u -v -90d +%Y-%m-%d 2>/dev/null || date -d '90 days ago' +%Y-%m-%d)"

# Parsing args (crude)
while [[ $# -gt 0 ]]; do
  case $1 in
    --start_full) START_FULL_VAL="$2"; shift 2 ;;
    --start_short) START_SHORT_VAL="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# ===== execute =====
run_bt "FULL"  "$START_FULL_VAL"  "$NOW_UTC"
run_bt "SHORT" "$START_SHORT_VAL" "$NOW_UTC"

# ===== Build benchmark_latest.json =====
echo "--- Compiling Benchmark Report ---"
mkdir -p reports

"$PY" - <<PY
import json
import os
from datetime import datetime
from pathlib import Path

def load_json(p):
    if not p.exists(): return {}
    return json.loads(p.read_text())

full_dir = Path("${OUT_DIR_FULL}")
short_dir = Path("${OUT_DIR_SHORT}")

data = {
    "schema_version": 1,
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "paths": {
        "FULL": str(full_dir / "summary.json"),
        "SHORT": str(short_dir / "summary.json")
    }
}

for kind, ddir in [("FULL", full_dir), ("SHORT", short_dir)]:
    summary = load_json(ddir / "summary.json")
    gate = load_json(ddir / "gate.json")
    
    data[kind] = {
        "run_dir": str(ddir),
        "top": summary,
        "per_symbol_4h": summary.get("per_symbol", {}),
        "gate_overall": gate.get("results", {}).get("overall", {"pass": False, "reasons": ["gate.json missing"]})
    }

out_path = Path("reports/benchmark_latest.json")
tmp_path = Path("reports/benchmark_latest.json.tmp")
with open(tmp_path, "w") as f:
    json.dump(data, f, indent=2)
os.rename(tmp_path, out_path)
print(f"Generated {out_path}")
PY

# ===== Final Table =====
"$PY" scripts/report_benchmark.py
