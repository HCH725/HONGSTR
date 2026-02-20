#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PY="${PY:-$REPO_ROOT/.venv/bin/python}"
if [[ ! -x "$PY" ]]; then
  echo "ERROR: venv python not found: $PY" >&2
  exit 1
fi

SYMBOLS="${SYMBOLS:-BTCUSDT ETHUSDT BNBUSDT}"
# BNB perpetual listing starts later than BTC/ETH; use a separate reasonable floor.
EARLIEST_FLOOR_DEFAULT="${EARLIEST_FLOOR_DEFAULT:-2020-01-02}"
EARLIEST_FLOOR_BNB="${EARLIEST_FLOOR_BNB:-2020-02-15}"
MAX_LAG_HOURS="${MAX_LAG_HOURS:-48}"

"$PY" - "$SYMBOLS" "$EARLIEST_FLOOR_DEFAULT" "$EARLIEST_FLOOR_BNB" "$MAX_LAG_HOURS" <<'PY'
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

symbols = [s.strip() for s in sys.argv[1].split() if s.strip()]
floor_default = dt.datetime.strptime(sys.argv[2], "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
floor_bnb = dt.datetime.strptime(sys.argv[3], "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
max_lag_hours = float(sys.argv[4])
now = dt.datetime.now(dt.timezone.utc)
max_lag = dt.timedelta(hours=max_lag_hours)

headers = [
    "SYMBOL",
    "ROWS",
    "EARLIEST_UTC",
    "LATEST_UTC",
    "AGE_HOURS",
    "EARLIEST_OK",
    "LATEST_OK",
    "STATUS",
]
rows_out = []
overall_ok = True

def extract_ts(record):
    for key in ("ts", "open_time", "open_time_ms", "timestamp", "tt"):
        if key in record and record[key] is not None:
            val = int(record[key])
            if val > 10_000_000_000:
                return dt.datetime.fromtimestamp(val / 1000, tz=dt.timezone.utc)
            return dt.datetime.fromtimestamp(val, tz=dt.timezone.utc)
    return None

def read_first_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                return json.loads(line)
    return None

def read_last_json(path: Path):
    proc = subprocess.run(
        ["tail", "-n", "1", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    line = proc.stdout.strip()
    if not line:
        return None
    return json.loads(line)

for sym in symbols:
    path = Path("data/derived") / sym / "1m" / "klines.jsonl"
    if not path.exists():
        rows_out.append([sym, "0", "MISSING", "MISSING", "INF", "NO", "NO", "FAIL"])
        overall_ok = False
        continue

    wc = subprocess.run(["wc", "-l", str(path)], capture_output=True, text=True, check=False)
    rows = wc.stdout.strip().split()[0] if wc.returncode == 0 and wc.stdout.strip() else "0"

    first_rec = read_first_json(path)
    last_rec = read_last_json(path)
    if not first_rec or not last_rec:
        rows_out.append([sym, rows, "EMPTY", "EMPTY", "INF", "NO", "NO", "FAIL"])
        overall_ok = False
        continue

    earliest = extract_ts(first_rec)
    latest = extract_ts(last_rec)
    if not earliest or not latest:
        rows_out.append([sym, rows, "BAD_TS", "BAD_TS", "INF", "NO", "NO", "FAIL"])
        overall_ok = False
        continue

    floor = floor_bnb if sym == "BNBUSDT" else floor_default
    earliest_ok = earliest <= floor
    lag = now - latest
    latest_ok = lag <= max_lag
    status = "PASS" if earliest_ok and latest_ok else "FAIL"
    if status == "FAIL":
        overall_ok = False

    rows_out.append(
        [
            sym,
            rows,
            earliest.strftime("%Y-%m-%d %H:%M:%S"),
            latest.strftime("%Y-%m-%d %H:%M:%S"),
            f"{lag.total_seconds()/3600:.2f}",
            "YES" if earliest_ok else "NO",
            "YES" if latest_ok else "NO",
            status,
        ]
    )

widths = []
for idx, header in enumerate(headers):
    width = len(header)
    for row in rows_out:
        width = max(width, len(str(row[idx])))
    widths.append(width)

line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
sep = "-+-".join("-" * w for w in widths)
print("=== DATA COVERAGE CHECK (1m) ===")
print(f"now_utc={now.strftime('%Y-%m-%d %H:%M:%S')} max_lag_hours={max_lag_hours}")
print(f"earliest_floor_default={floor_default.strftime('%Y-%m-%d')} earliest_floor_bnb={floor_bnb.strftime('%Y-%m-%d')}")
print(line)
print(sep)
for row in rows_out:
    print(" | ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers))))

if overall_ok:
    print("OVERALL_STATUS=PASS")
else:
    print("OVERALL_STATUS=FAIL")
    raise SystemExit(1)
PY
