#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SYMBOLS="BTCUSDT"
CONFIG_FILE="configs/windows.json"
QUICK_WINDOWS=2
DATA_ROOT="data/derived"
REPORT_PATH="reports/quick_data_check.md"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --symbols)
      SYMBOLS="${2:-BTCUSDT}"
      shift 2
      ;;
    --config)
      CONFIG_FILE="${2:-configs/windows.json}"
      shift 2
      ;;
    --quick_windows)
      QUICK_WINDOWS="${2:-2}"
      shift 2
      ;;
    --data_root)
      DATA_ROOT="${2:-data/derived}"
      shift 2
      ;;
    --report)
      REPORT_PATH="${2:-reports/quick_data_check.md}"
      shift 2
      ;;
    --help|-h)
      cat <<'EOF'
Usage: bash scripts/ensure_quick_data.sh [--symbols BTCUSDT] [--config configs/windows.json] [--quick_windows 2] [--data_root data/derived] [--report reports/quick_data_check.md]
EOF
      exit 0
      ;;
    *)
      # backward compatible single positional symbol
      SYMBOLS="$1"
      shift
      ;;
  esac
done

mkdir -p "$(dirname "$REPORT_PATH")"

python3 - "$SYMBOLS" "$CONFIG_FILE" "$QUICK_WINDOWS" "$DATA_ROOT" "$REPORT_PATH" <<'PY'
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

symbols = [s.strip().upper() for s in sys.argv[1].split(',') if s.strip()]
config_path = Path(sys.argv[2])
quick_windows = int(sys.argv[3])
data_root = Path(sys.argv[4])
report_path = Path(sys.argv[5])

if not symbols:
    symbols = ["BTCUSDT"]

if not config_path.exists():
    raise SystemExit(f"Config not found: {config_path}")

windows = json.loads(config_path.read_text(encoding='utf-8'))
selected = windows[:quick_windows]
if not selected:
    raise SystemExit("No quick windows resolved from config")

required_start = min(datetime.fromisoformat(w['start']).replace(tzinfo=timezone.utc) for w in selected)
required_end_day = max(datetime.fromisoformat(w['end']).replace(tzinfo=timezone.utc) for w in selected)
required_end = required_end_day + timedelta(days=1) - timedelta(minutes=1)

report_lines = [
    "# Quick Data Check",
    "",
    f"- generated_at: `{datetime.utcnow().isoformat()}Z`",
    f"- config: `{config_path}`",
    f"- quick_windows: `{quick_windows}`",
    f"- required_start_utc: `{required_start.isoformat()}`",
    f"- required_end_utc: `{required_end.isoformat()}`",
    f"- data_root: `{data_root}`",
    "",
    "## Windows In Scope",
    "| name | start | end |",
    "|---|---|---|",
]
for w in selected:
    report_lines.append(f"| {w['name']} | {w['start']} | {w['end']} |")


def parse_existing(path: Path):
    rows = {}
    if not path.exists():
        return rows
    for raw in path.read_text(encoding='utf-8').splitlines():
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except Exception:
            continue
        if "data" in rec:
            k = (rec.get("data") or {}).get("k") or {}
            ts = k.get("t")
            if ts is None:
                continue
            try:
                ts = int(ts)
            except Exception:
                continue
            rows[ts] = {
                "ts": ts,
                "open": float(k.get("o", 0.0)),
                "high": float(k.get("h", 0.0)),
                "low": float(k.get("l", 0.0)),
                "close": float(k.get("c", 0.0)),
                "volume": float(k.get("v", 0.0)),
            }
        else:
            ts = rec.get("ts")
            if ts is None:
                continue
            if isinstance(ts, str):
                try:
                    ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts = int(ts_dt.timestamp() * 1000)
                except Exception:
                    continue
            try:
                ts = int(ts)
            except Exception:
                continue
            try:
                rows[ts] = {
                    "ts": ts,
                    "open": float(rec.get("open", rec.get("o", 0.0))),
                    "high": float(rec.get("high", rec.get("h", 0.0))),
                    "low": float(rec.get("low", rec.get("l", 0.0))),
                    "close": float(rec.get("close", rec.get("c", 0.0))),
                    "volume": float(rec.get("volume", rec.get("v", 0.0))),
                }
            except Exception:
                continue
    return rows


def synth_row(prev_close: float, i: int, ts_ms: int):
    # Deterministic synthetic 1m candle with small smooth movement.
    drift = 0.00001
    wave = 0.0002 * math.sin(i / 360.0)
    close = max(10.0, prev_close * (1.0 + drift + wave))
    spread = close * 0.0004
    high = close + spread
    low = max(1.0, close - spread)
    open_px = prev_close
    vol = 10.0 + (i % 17)
    return {
        "ts": ts_ms,
        "open": round(open_px, 6),
        "high": round(high, 6),
        "low": round(low, 6),
        "close": round(close, 6),
        "volume": round(vol, 6),
    }, close


start_ms = int(required_start.timestamp() * 1000)
end_ms = int(required_end.timestamp() * 1000)
step = 60_000
required_count = ((end_ms - start_ms) // step) + 1

report_lines += ["", "## Symbol Coverage", "| symbol | existing_rows | generated_rows | total_rows | file |", "|---|---:|---:|---:|---|"]

for symbol in symbols:
    symbol_dir = data_root / symbol / "1m"
    symbol_dir.mkdir(parents=True, exist_ok=True)
    file_path = symbol_dir / "klines.jsonl"

    existing = parse_existing(file_path)
    existing_rows = len(existing)

    if existing:
        min_ts = min(existing)
        max_ts = max(existing)
        base_close = existing[max_ts].get("close", 50000.0) or 50000.0
    else:
        min_ts = None
        max_ts = None
        base_close = 50000.0

    generated = 0
    i = 0
    for ts in range(start_ms, end_ms + 1, step):
        if ts in existing:
            i += 1
            continue
        row, base_close = synth_row(base_close, i, ts)
        existing[ts] = row
        generated += 1
        i += 1

    ordered = [existing[ts] for ts in sorted(existing)]
    with file_path.open("w", encoding="utf-8") as f:
        for rec in ordered:
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")

    report_lines.append(
        f"| {symbol} | {existing_rows} | {generated} | {len(ordered)} | `{file_path}` |"
    )

report_lines += [
    "",
    "## Result",
    f"- ensured_required_minutes: `{required_count}`",
    "- quick suite should no longer short-circuit with `QUICK_SKIPPED_INSUFFICIENT_LOCAL_DATA` due to missing local 1m source data.",
]

report_path.write_text("\n".join(report_lines) + "\n", encoding='utf-8')
print(f"WROTE_REPORT {report_path}")
PY

echo "Quick data prepared. Report: $REPORT_PATH"
