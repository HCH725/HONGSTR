import argparse
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
    # Backtest runner expects: {"ts": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}
    # fetch_klines returns df with numeric columns and ts as index.

    df_out = df.copy()
    df_out["ts"] = df_out.index.map(lambda x: int(x.timestamp() * 1000))

    with open(out_file, "w") as f:
        for _, row in df_out.iterrows():
            record = {
                "ts": int(row["ts"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
            import json

            f.write(json.dumps(record) + "\n")

    print(f"Successfully saved {len(df)} rows to {out_file}")


if __name__ == "__main__":
    main()
