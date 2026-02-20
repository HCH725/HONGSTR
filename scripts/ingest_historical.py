import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Path Hack
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from hongstr.data.ingest import fetch_klines


def str_to_ms(date_str: str) -> int:
    if date_str == "now":
        return int(datetime.utcnow().timestamp() * 1000)
    dt = pd.to_datetime(date_str)
    if dt.tz is None:
        dt = dt.tz_localize("UTC")
    return int(dt.timestamp() * 1000)


def parse_existing_record(raw: dict):
    """Normalize existing jsonl rows to canonical {ts, open, high, low, close, volume}."""
    if not isinstance(raw, dict):
        return None

    if "data" in raw:
        k = (raw.get("data") or {}).get("k") or {}
        ts_val = k.get("t")
        o = k.get("o")
        h = k.get("h")
        l = k.get("l")
        c = k.get("c")
        v = k.get("v")
    else:
        ts_val = raw.get("ts")
        o = raw.get("open", raw.get("o"))
        h = raw.get("high", raw.get("h"))
        l = raw.get("low", raw.get("l"))
        c = raw.get("close", raw.get("c"))
        v = raw.get("volume", raw.get("v"))

    if ts_val is None:
        return None
    try:
        if isinstance(ts_val, str):
            ts_ms = int(pd.to_datetime(ts_val, utc=True).timestamp() * 1000)
        else:
            ts_ms = int(ts_val)
        return {
            "ts": ts_ms,
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": float(v),
        }
    except Exception:
        return None


def load_existing_rows(path: Path):
    rows = {}
    if not path.exists():
        return rows

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            norm = parse_existing_record(rec)
            if norm is None:
                continue
            rows[norm["ts"]] = norm
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Wrapper for historical data ingestion"
    )
    parser.add_argument(
        "--symbol", type=str, required=True, help="Symbol to fetch (e.g. BTCUSDT)"
    )
    parser.add_argument("--start", type=str, default="2021-01-01", help="Start date")
    parser.add_argument("--end", type=str, default="now", help="End date")
    parser.add_argument(
        "--interval",
        type=str,
        default="1m",
        help="Interval (fixed to 1m for backtest source)",
    )
    parser.add_argument(
        "--data_root", type=str, default="data/derived", help="Data root directory"
    )
    parser.add_argument(
        "--market", type=str, default="futures", help="Market type (futures/spot)"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing klines.jsonl instead of merge+dedupe by timestamp",
    )
    args = parser.parse_args()

    symbol = args.symbol.upper()
    start_ms = str_to_ms(args.start)
    end_ms = str_to_ms(args.end)

    print(f"Ingesting {symbol} {args.interval} from {args.start} to {args.end}...")

    # fetch_klines in ingest.py is already set for fapi/v1/klines (Futures)
    # If market=spot, fetch_klines would need modification,
    # but for HONGSTR purpose, Futures is the primary target.

    df = fetch_klines(symbol, start_ms, end_ms)

    if df.empty:
        print(f"No data fetched for {symbol}")
        sys.exit(1)

    out_dir = Path(args.data_root) / symbol / args.interval
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "klines.jsonl"

    # Save to jsonl as required.
    # Backtest runner expects: {"ts": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}  # noqa: E501
    # fetch_klines returns df with numeric columns and ts as index.

    df_out = df.copy().sort_index()
    df_out["ts"] = df_out.index.map(lambda x: int(x.timestamp() * 1000))

    new_rows = {}
    for _, row in df_out.iterrows():
        ts = int(row["ts"])
        new_rows[ts] = {
            "ts": ts,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }

    existing_count = 0
    if args.overwrite:
        merged_rows = new_rows
    else:
        merged_rows = load_existing_rows(out_file)
        existing_count = len(merged_rows)
        merged_rows.update(new_rows)

    ordered = [merged_rows[k] for k in sorted(merged_rows)]
    tmp_file = out_file.with_suffix(".jsonl.tmp")
    with open(tmp_file, "w", encoding="utf-8") as handle:
        for rec in ordered:
            handle.write(json.dumps(rec, separators=(",", ":")) + "\n")
    tmp_file.replace(out_file)

    print(
        f"Saved {len(new_rows)} fetched rows; merged_total={len(ordered)} "
        f"(existing={existing_count}, overwrite={args.overwrite}) -> {out_file}"
    )


if __name__ == "__main__":
    main()
