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
START_DATE="${START_DATE:-2020-01-01}"
END_DATE="${END_DATE:-now}"

echo "=== BACKFILL 1m from $START_DATE to $END_DATE ==="
echo "PY=$PY"
"$PY" - <<'PY'
import ssl
print("PYTHON_OK:", ssl.OPENSSL_VERSION)
PY

for sym in $SYMBOLS; do
  echo ">> Backfill $sym 1m: $START_DATE -> $END_DATE"
  "$PY" scripts/ingest_historical.py --symbol "$sym" --tf "1m" --start "$START_DATE" --end "$END_DATE"

  echo ">> Aggregate $sym from 1m source"
  "$PY" scripts/aggregate_data.py --symbol "$sym"
done

echo "=== BACKFILL COMPLETE ==="
