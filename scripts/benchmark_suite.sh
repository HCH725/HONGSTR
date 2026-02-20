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
    --slippage_bps "$SLIP_BPS" 2>&1)
  local EXIT_CODE=$?
  set -e
  echo "$PIPE_OUT"

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
# Prefer dataset end date instead of wall-clock "now", so SHORT window stays valid
# when local historical data is stale.
NOW_UTC="$("$PY" - "$SYMBOLS" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import json
import pandas as pd
import sys

symbols = [s.strip().upper() for s in sys.argv[1].split(",") if s.strip()]
latest = None

for sym in symbols:
    pq = Path("data") / f"{sym}_1m.parquet"
    if pq.exists():
        try:
            col = pd.read_parquet(pq, columns=["open_time"])["open_time"]
            ts = pd.to_datetime(col, utc=True).max()
            if pd.notna(ts):
                latest = ts if latest is None else max(latest, ts)
                continue
        except Exception:
            pass

    # Fallback: read last valid line from derived jsonl
    j = Path("data/derived") / sym / "1m" / "klines.jsonl"
    if j.exists():
        try:
            last_ts = None
            with j.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        ts = rec.get("ts")
                        if isinstance(ts, int):
                            last_ts = ts
                    except Exception:
                        continue
            if last_ts is not None:
                ts = datetime.fromtimestamp(last_ts / 1000.0, tz=timezone.utc)
                latest = ts if latest is None else max(latest, ts)
        except Exception:
            pass

if latest is None:
    latest = datetime.now(timezone.utc)
print(latest.strftime("%Y-%m-%d"))
PY
)"
# CLI Overrides (Simple parsing)
START_FULL_VAL="2020-01-01"
START_SHORT_VAL="$("$PY" - "$NOW_UTC" <<'PY'
from datetime import timedelta
import pandas as pd
import sys

end = pd.to_datetime(sys.argv[1], utc=True)
start = end - timedelta(days=90)
print(start.strftime("%Y-%m-%d"))
PY
)"

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
