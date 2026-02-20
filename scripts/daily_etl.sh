#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Force venv python to avoid system LibreSSL runtime.
PY="${PY:-$REPO_ROOT/.venv/bin/python}"
if [[ ! -x "$PY" ]]; then
  echo "ERROR: venv python not found: $PY" >&2
  echo "HINT: /opt/homebrew/bin/python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ." >&2
  exit 1
fi

SYMBOLS="${SYMBOLS:-BTCUSDT ETHUSDT BNBUSDT}"
OVERLAP_DAYS="${OVERLAP_DAYS:-2}"
FALLBACK_START="${FALLBACK_START:-2020-01-01}"
END_DATE="${END_DATE:-now}"
COVERAGE_STRICT="${COVERAGE_STRICT:-0}"

echo "=== Daily ETL Started ($(date)) ==="
echo "PY=$PY"
"$PY" - <<'PY'
import ssl
print("PYTHON_OK:", ssl.OPENSSL_VERSION)
PY

calc_start() {
  local sym="$1"
  "$PY" - <<PY
import datetime
import json
from pathlib import Path

symbol = "$sym"
fallback = "$FALLBACK_START"
overlap_days = int("$OVERLAP_DAYS")
path = Path(f"data/derived/{symbol}/1m/klines.jsonl")

def parse_ts(rec):
    ts = rec.get("ts") or rec.get("open_time") or rec.get("open_time_ms") or rec.get("timestamp") or rec.get("tt")
    if ts is None:
        return None
    ts = int(ts)
    if ts > 10_000_000_000:  # ms
        return datetime.datetime.utcfromtimestamp(ts / 1000)
    return datetime.datetime.utcfromtimestamp(ts)

def read_last_nonempty_line(p: Path):
    if not p.exists():
        return None
    last = None
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = line
    return last

last_line = read_last_nonempty_line(path)
if not last_line:
    print(fallback)
    raise SystemExit(0)

try:
    record = json.loads(last_line)
except Exception:
    print(fallback)
    raise SystemExit(0)

dt = parse_ts(record)
if dt is None:
    print(fallback)
    raise SystemExit(0)

start_dt = dt - datetime.timedelta(days=overlap_days)
floor_dt = datetime.datetime.strptime(fallback, "%Y-%m-%d")
if start_dt < floor_dt:
    start_dt = floor_dt
print(start_dt.strftime("%Y-%m-%d"))
PY
}

for sym in $SYMBOLS; do
  START_DATE="$(calc_start "$sym")"
  echo ">> Processing $sym"
  echo "   start=$START_DATE end=$END_DATE (overlap_days=$OVERLAP_DAYS)"
  set +e
  "$PY" scripts/ingest_historical.py --symbol "$sym" --tf "1m" --start "$START_DATE" --end "$END_DATE"
  INGEST_RC=$?
  set -e
  if [[ "$INGEST_RC" -ne 0 ]]; then
    echo "WARN: ingest_historical failed for $sym (rc=$INGEST_RC); fallback to realtime merge"
    "$PY" scripts/merge_realtime_into_derived.py --symbol "$sym"
  fi
  "$PY" scripts/aggregate_data.py --symbol "$sym"
done

echo "=== Coverage Check ==="
if ! bash scripts/check_data_coverage.sh; then
  if [[ "$COVERAGE_STRICT" == "1" ]]; then
    echo "ERROR: coverage check failed (COVERAGE_STRICT=1)" >&2
    exit 2
  fi
  echo "WARN: coverage check failed (set COVERAGE_STRICT=1 to enforce failure)" >&2
fi

echo "=== Daily ETL Complete ($(date)) ==="
