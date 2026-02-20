#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Force venv python (avoid system python / LibreSSL).
PY="${PY:-$REPO_ROOT/.venv/bin/python}"
if [[ ! -x "$PY" ]]; then
  echo "ERROR: venv python not found: $PY" >&2
  exit 1
fi

SYMBOLS="${SYMBOLS:-BTCUSDT ETHUSDT BNBUSDT}"
START_DATE="${START_DATE:-2020-01-01}"
END_DATE="${END_DATE:-now}"
OVERLAP_DAYS="${OVERLAP_DAYS:-2}"
declare -a SYM_LIST=()
declare -a PRE_SYNC_STARTS=()

echo "=== BACKFILL 1m from $START_DATE to $END_DATE ==="
echo "PY=$PY"
"$PY" - <<'PY'
import ssl
print("PYTHON_OK:", ssl.OPENSSL_VERSION)
PY

SYMBOLS_CSV="$(echo "$SYMBOLS" | tr ' ' ',' | tr -s ',')"

calc_start_from_derived() {
  local sym="$1"
  "$PY" - <<PY
import datetime
import json
from pathlib import Path

symbol = "$sym"
fallback = "$START_DATE"
overlap_days = int("$OVERLAP_DAYS")
path = Path(f"data/derived/{symbol}/1m/klines.jsonl")

def parse_ts(rec):
    ts = rec.get("ts") or rec.get("open_time") or rec.get("open_time_ms") or rec.get("timestamp") or rec.get("tt")
    if ts is None:
        return None
    ts = int(ts)
    if ts > 10_000_000_000:
        return datetime.datetime.utcfromtimestamp(ts / 1000)
    return datetime.datetime.utcfromtimestamp(ts)

last = None
if path.exists():
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = line

if not last:
    print(fallback)
    raise SystemExit(0)

try:
    rec = json.loads(last)
except Exception:
    print(fallback)
    raise SystemExit(0)

dt = parse_ts(rec)
if dt is None:
    print(fallback)
    raise SystemExit(0)

start = dt - datetime.timedelta(days=overlap_days)
floor = datetime.datetime.strptime(fallback, "%Y-%m-%d")
if start < floor:
    start = floor
print(start.strftime("%Y-%m-%d"))
PY
}

for sym in $SYMBOLS; do
  SYM_LIST+=("$sym")
  PRE_SYNC_STARTS+=("$(calc_start_from_derived "$sym")")
done

echo "=== [1/3] Sync baseline from local parquet ==="
set +e
"$PY" scripts/sync_derived_from_parquet.py \
  --symbols "$SYMBOLS_CSV" \
  --start "$START_DATE" \
  --end "$END_DATE" \
  --tfs "1h,4h"
SYNC_RC=$?
set -e
if [[ "$SYNC_RC" -ne 0 ]]; then
  echo "WARN: sync_derived_from_parquet failed rc=$SYNC_RC; fallback to direct ingest for full range"
fi

echo "=== [2/3] Top off latest candles from exchange (merge+dedupe) ==="
for i in "${!SYM_LIST[@]}"; do
  sym="${SYM_LIST[$i]}"
  TOP_OFF_START="$(calc_start_from_derived "$sym")"
  PRE_START="${PRE_SYNC_STARTS[$i]:-$START_DATE}"
  if [[ "$PRE_START" > "$TOP_OFF_START" ]]; then
    TOP_OFF_START="$PRE_START"
  fi

  echo ">> Backfill/top-off $sym 1m: $TOP_OFF_START -> $END_DATE"
  set +e
  "$PY" scripts/ingest_historical.py --symbol "$sym" --tf "1m" --start "$TOP_OFF_START" --end "$END_DATE"
  INGEST_RC=$?
  set -e
  if [[ "$INGEST_RC" -ne 0 ]]; then
    echo "WARN: top-off ingest failed for $sym (rc=$INGEST_RC); fallback to realtime merge"
    "$PY" scripts/merge_realtime_into_derived.py --symbol "$sym"
  fi
  "$PY" scripts/aggregate_data.py --symbol "$sym"
done

echo "=== [3/3] Coverage check ==="
bash scripts/check_data_coverage.sh

echo "=== BACKFILL COMPLETE ==="
