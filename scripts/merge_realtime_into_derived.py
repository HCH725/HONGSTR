#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def normalize_existing(raw: dict):
    ts = raw.get("ts") or raw.get("open_time") or raw.get("open_time_ms") or raw.get("timestamp") or raw.get("tt")
    if ts is None:
        return None
    try:
        return {
            "ts": int(ts),
            "open": float(raw.get("open", raw.get("o"))),
            "high": float(raw.get("high", raw.get("h"))),
            "low": float(raw.get("low", raw.get("l"))),
            "close": float(raw.get("close", raw.get("c"))),
            "volume": float(raw.get("volume", raw.get("v"))),
        }
    except Exception:
        return None


def normalize_realtime(raw: dict, symbol: str):
    data = raw.get("data") or {}
    k = data.get("k") or {}
    if data.get("s") != symbol and k.get("s") != symbol:
        return None
    if str(k.get("i")) != "1m":
        return None
    # Keep only closed bars.
    if bool(k.get("x")) is not True:
        return None
    ts = k.get("t")
    if ts is None:
        return None
    try:
        return {
            "ts": int(ts),
            "open": float(k.get("o")),
            "high": float(k.get("h")),
            "low": float(k.get("l")),
            "close": float(k.get("c")),
            "volume": float(k.get("v")),
        }
    except Exception:
        return None


def load_derived(path: Path):
    rows = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except Exception:
                continue
            rec = normalize_existing(raw)
            if rec is None:
                continue
            rows[rec["ts"]] = rec
    return rows


def load_realtime(symbol: str, realtime_root: Path):
    rows = {}
    pattern = f"kline_{symbol}_1m.jsonl"
    for day_dir in sorted(realtime_root.glob("*")):
        if not day_dir.is_dir():
            continue
        file_path = day_dir / pattern
        if not file_path.exists():
            continue
        with file_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except Exception:
                    continue
                rec = normalize_realtime(raw, symbol)
                if rec is None:
                    continue
                rows[rec["ts"]] = rec
    return rows


def write_derived(path: Path, rows: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for ts in sorted(rows):
            fh.write(json.dumps(rows[ts], separators=(",", ":")) + "\n")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge closed realtime kline_1m rows into data/derived/<SYMBOL>/1m/klines.jsonl")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--realtime_root", default="data/realtime")
    parser.add_argument("--derived_root", default="data/derived")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    derived_path = Path(args.derived_root) / symbol / "1m" / "klines.jsonl"
    realtime_root = Path(args.realtime_root)

    existing = load_derived(derived_path)
    before = len(existing)
    rt_rows = load_realtime(symbol, realtime_root)
    rt_count = len(rt_rows)
    if rt_count == 0:
        print(f"No realtime 1m rows found for {symbol} under {realtime_root}")
        return 1

    existing.update(rt_rows)
    write_derived(derived_path, existing)
    after = len(existing)
    print(
        f"Merged realtime into derived for {symbol}: "
        f"realtime_rows={rt_count} before={before} after={after} path={derived_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
