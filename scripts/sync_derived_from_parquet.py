#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from hongstr.data.aggregate import resample_klines  # noqa: E402


def parse_ts(value: str) -> pd.Timestamp:
    if value == "now":
        return pd.Timestamp.now(tz="UTC")
    ts = pd.to_datetime(value, utc=True)
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    return ts


def write_jsonl(df: pd.DataFrame, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with open(tmp, "w", encoding="utf-8") as handle:
        for row in df.itertuples():
            rec = {
                "ts": int(row.Index.timestamp() * 1000),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
            }
            handle.write(json.dumps(rec, separators=(",", ":")) + "\n")
            count += 1
    tmp.replace(path)
    return count


def load_parquet_as_1m(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path, columns=["open_time", "open", "high", "low", "close", "volume"])
    if "open_time" not in df.columns:
        raise ValueError(f"{path} missing open_time column")
    df["ts"] = pd.to_datetime(df["open_time"], utc=True)
    df = df.drop(columns=["open_time"])
    df = df.dropna(subset=["ts", "open", "high", "low", "close", "volume"])
    df = df.set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync data/derived/<SYMBOL>/<TF>/klines.jsonl from local data/<SYMBOL>_1m.parquet"
    )
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,BNBUSDT")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="now")
    parser.add_argument("--data_dir", default="data")
    parser.add_argument("--derived_root", default="data/derived")
    parser.add_argument("--tfs", default="1h,4h")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    tfs = [tf.strip() for tf in args.tfs.split(",") if tf.strip()]
    start_ts = parse_ts(args.start)
    end_ts = parse_ts(args.end)
    data_dir = Path(args.data_dir)
    derived_root = Path(args.derived_root)

    if not symbols:
        print("No symbols resolved from --symbols", file=sys.stderr)
        return 2
    if end_ts < start_ts:
        print(f"Invalid range: end({end_ts}) < start({start_ts})", file=sys.stderr)
        return 2

    failures = []
    for sym in symbols:
        parquet_path = data_dir / f"{sym}_1m.parquet"
        if not parquet_path.exists():
            failures.append(f"{sym}: missing {parquet_path}")
            continue

        try:
            df_1m = load_parquet_as_1m(parquet_path)
        except Exception as exc:
            failures.append(f"{sym}: load parquet failed: {exc}")
            continue

        df_1m = df_1m[(df_1m.index >= start_ts) & (df_1m.index <= end_ts)]
        if df_1m.empty:
            failures.append(f"{sym}: no rows in requested range {start_ts}..{end_ts}")
            continue

        out_1m = derived_root / sym / "1m" / "klines.jsonl"
        n_1m = write_jsonl(df_1m, out_1m)
        print(
            f"SYNC symbol={sym} tf=1m rows={n_1m} "
            f"start={df_1m.index.min().isoformat()} end={df_1m.index.max().isoformat()} "
            f"path={out_1m}"
        )

        for tf in tfs:
            try:
                df_tf = resample_klines(df_1m, tf)
            except Exception as exc:
                failures.append(f"{sym}: resample {tf} failed: {exc}")
                continue

            out_tf = derived_root / sym / tf / "klines.jsonl"
            n_tf = write_jsonl(df_tf, out_tf)
            if n_tf == 0:
                failures.append(f"{sym}: generated 0 rows for tf={tf}")
                continue
            print(
                f"SYNC symbol={sym} tf={tf} rows={n_tf} "
                f"start={df_tf.index.min().isoformat()} end={df_tf.index.max().isoformat()} "
                f"path={out_tf}"
            )

    if failures:
        for msg in failures:
            print(f"ERROR {msg}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
