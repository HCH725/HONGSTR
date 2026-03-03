#!/usr/bin/env python3
"""
Probe earliest available Binance Futures metrics and write coverage SSOT.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from futures_metrics_lib import (
    DEFAULT_COVERAGE_PATH,
    DEFAULT_SYMBOLS,
    DEFAULT_TARGET_START,
    PROBE_METRICS,
    compose_coverage_row,
    find_coverage_row,
    load_coverage_rows,
    parse_date_floor,
    probe_earliest_available,
    upsert_coverage_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe earliest available Binance Futures metrics.")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--metrics", nargs="+", default=list(PROBE_METRICS))
    parser.add_argument("--start-date", default=DEFAULT_TARGET_START)
    parser.add_argument("--probe-step-days", type=int, default=31)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--coverage-path", default=str(DEFAULT_COVERAGE_PATH))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    coverage_path = repo_root / args.coverage_path
    start_dt = parse_date_floor(args.start_date)
    coverage_rows = load_coverage_rows(coverage_path)
    updates: list[dict] = []

    for symbol in args.symbols:
        for metric in args.metrics:
            existing = find_coverage_row(coverage_rows, symbol, metric)
            probe = probe_earliest_available(
                metric=metric,
                symbol=symbol,
                start_dt=start_dt,
                probe_step_days=args.probe_step_days,
            )
            row = compose_coverage_row(
                repo_root=repo_root,
                symbol=symbol,
                metric=metric,
                existing_row=existing,
                source_earliest_utc=probe.get("earliest_utc"),
                source_latest_utc=probe.get("latest_utc"),
                status=str(probe.get("status") or "UNKNOWN"),
                reason=str(probe.get("reason") or ""),
            )
            updates.append(row)
            print(
                f"{symbol} {metric} status={row['status']} "
                f"earliest={row['earliest_utc']} latest={row['latest_utc']} reason={row['reason']}"
            )

    upsert_coverage_rows(coverage_path, updates)
    print(f"coverage_path={coverage_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
