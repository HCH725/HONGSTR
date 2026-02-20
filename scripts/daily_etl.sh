#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Force venv python (avoid system python/LibreSSL)
PY="${PY:-$REPO_ROOT/.venv/bin/python}"
if [ ! -x "$PY" ]; then
  echo "ERROR: venv python not found: $PY"
  exit 1
fi

SYMBOLS="${SYMBOLS:-BTCUSDT ETHUSDT BNBUSDT}"
# how many days to overlap backwards from last candle time (safety for gaps/reorg)
OVERLAP_DAYS="${OVERLAP_DAYS:-2}"
# if no data exists yet, start from here
FALLBACK_START="${FALLBACK_START:-2020-01-01}"
END_DATE="${END_DATE:-now}"

echo "=== Daily ETL Started ($(date)) ==="
echo "PY=$PY"
"$PY" - <<'PY'
import ssl
print("PYTHON_OK:", ssl.OPENSSL_VERSION)
PY

calc_start () {
  local sym="$1"
  "$PY" - <<PY
import json, datetime
from pathlib import Path

sym="$sym"
p=Path(f"data/derived/{sym}/1m/klines.jsonl")
fallback="${FALLBACK_START}"
overlap_days=int("${OVERLAP_DAYS}")

def parse_last_ts(path: Path):
    if not path.exists():
        return None
    last=None
    with path.open() as f:
        for line in f:
            if line.strip():
                last=line
    if not last:
        return None
    obj=json.loads(last)
    ts=obj.get("ts") or obj.get("open_time") or obj.get("open_time_ms") or obj.get("tt") or obj.get("timestamp")
    if ts is None:
        return None
    if ts > 10_000_000_000:  # ms
        dt=datetime.datetime.utcfromtimestamp(ts/1000)
    else:
        dt=datetime.datetime.utcfromtimestamp(ts)
    return dt

dt=parse_last_ts(p)
if dt is None:
    print(fallback)
else:
    start_dt = dt - datetime.timedelta(days=overlap_days)
    # never earlier than fallback
    fb=datetime.datetime.fromisoformat(fallback)
    if start_dt < fb:
        start_dt = fb
    print(start_dt.strftime("%Y-%m-%d"))
PY
}

for sym in $SYMBOLS; do
  START_DATE="$(calc_start "$sym")"
  echo ">> Processing $sym"
  echo "   start=$START_DATE end=$END_DATE (overlap_days=$OVERLAP_DAYS)"
  "$PY" scripts/ingest_historical.py --symbol "$sym" --tf "1m" --start "$START_DATE" --end "$END_DATE"
  "$PY" scripts/aggregate_data.py --symbol "$sym"
done

echo "=== Daily ETL Complete ($(date)) ==="
