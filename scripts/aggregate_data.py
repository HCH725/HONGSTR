import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

# Path Hack
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from hongstr.data.aggregate import resample_klines


def main():
    parser = argparse.ArgumentParser(description="Wrapper for kline aggregation")
    parser.add_argument(
        "--symbol", type=str, required=True, help="Symbol (e.g. BTCUSDT)"
    )
    parser.add_argument(
        "--data_root", type=str, default="data/derived", help="Data root directory"
    )
    parser.add_argument(
        "--tfs", type=str, default="5m,15m,1h,4h", help="Target timeframes"
    )
    args = parser.parse_args()

    symbol = args.symbol.upper()
    tfs = [tf.strip() for tf in args.tfs.split(",")]

    src_file = Path(args.data_root) / symbol / "1m" / "klines.jsonl"
    if not src_file.exists():
        print(
            f"Source file not found: {src_file}. Please run ingest_historical.py first."
        )
        sys.exit(1)

    print(f"Aggregating {symbol} from 1m source...")

    # Load 1m
    data = []
    with open(src_file, "r") as f:
        for line in f:
            try:
                record = json.loads(line)
                data.append(record)
            except:  # noqa: E722
                continue

    df_1m = pd.DataFrame(data)
    if df_1m.empty:
        print("Empty source data")
        sys.exit(1)

    df_1m["ts"] = pd.to_datetime(df_1m["ts"], unit="ms", utc=True)
    df_1m.set_index("ts", inplace=True)

    for tf in tfs:
        print(f"  Timeframe: {tf}...")
        df_tf = resample_klines(df_1m, tf)

        out_dir = Path(args.data_root) / symbol / tf
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "klines.jsonl"

        # Save to jsonl
        df_out = df_tf.reset_index()
        # Rename open_time if it's named 'ts' after resample or keep as index
        if "ts" not in df_out.columns and "open_time" in df_out.columns:
            df_out.rename(columns={"open_time": "ts"}, inplace=True)

        # Ensure 'ts' is ms or iso as runner expects
        # Runner's load_1m_data looks for k['t'] in 'data' OR record['ts']

        records = []
        for _, row in df_out.iterrows():
            records.append(
                {
                    "ts": int(row["ts"].timestamp() * 1000),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )

        with open(out_file, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        print(f"    Saved {len(df_tf)} rows to {out_file}")


if __name__ == "__main__":
    main()
