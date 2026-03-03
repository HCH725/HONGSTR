#!/usr/bin/env python3
"""
Rolling Binance Futures metrics fetcher.

Default mode: fetch recent windows for research coverage, update local jsonl storage,
and refresh data/state/futures_metrics_coverage_latest.json.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

from futures_metrics_lib import (
    DEFAULT_COVERAGE_PATH,
    DEFAULT_SYMBOLS,
    DEFAULT_TARGET_START,
    HISTORICAL_METRICS,
    ROLLING_METRICS,
    BinanceAPIError,
    compose_coverage_row,
    find_coverage_row,
    load_coverage_rows,
    probe_earliest_available,
    probe_liquidations,
    to_iso_utc,
    upsert_coverage_rows,
    utc_now,
    write_metric_rows,
    fetch_metric_range,
    fetch_metric_snapshot,
    parse_date_floor,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch rolling Binance Futures metrics.")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--metrics", nargs="+", default=list(ROLLING_METRICS))
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--skip-probe", action="store_true")
    parser.add_argument("--probe-step-days", type=int, default=31)
    parser.add_argument("--skip-liquidations-probe", action="store_true")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--coverage-path", default=str(DEFAULT_COVERAGE_PATH))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    coverage_path = repo_root / args.coverage_path
    now_dt = utc_now()
    rolling_start = now_dt - timedelta(days=max(1, args.days))
    target_start = parse_date_floor(DEFAULT_TARGET_START)
    coverage_rows = load_coverage_rows(coverage_path)
    updates: list[dict] = []
    failures: list[str] = []

    for symbol in args.symbols:
        for metric in args.metrics:
            existing = find_coverage_row(coverage_rows, symbol, metric)
            source_earliest = str((existing or {}).get("earliest_utc") or "").strip() or None
            source_latest = None
            status = "OK"
            reason = ""
            added_rows = 0

            if not args.skip_probe and metric in HISTORICAL_METRICS and not source_earliest:
                try:
                    probe = probe_earliest_available(
                        metric=metric,
                        symbol=symbol,
                        start_dt=target_start,
                        now_dt=now_dt,
                        probe_step_days=args.probe_step_days,
                    )
                    source_earliest = probe.get("earliest_utc") or source_earliest
                    if probe.get("status") == "FAIL":
                        status = "WARN"
                        reason = f"probe_failed:{probe.get('reason')}"
                    elif probe.get("status") == "WARN":
                        status = "WARN"
                        reason = str(probe.get("reason") or "probe_warn")
                except BinanceAPIError as exc:
                    status = "WARN"
                    reason = f"probe_failed:{exc.reason}"

            try:
                if metric in HISTORICAL_METRICS:
                    rows = fetch_metric_range(metric, symbol, rolling_start, now_dt)
                else:
                    rows = fetch_metric_snapshot(metric, symbol)
                if rows:
                    added_rows = write_metric_rows(repo_root, symbol, metric, rows)
                    source_latest = rows[-1]["ts_utc"]
                    if metric == "premium_index":
                        source_earliest = rows[0]["ts_utc"]
                        reason = "snapshot_only_endpoint"
                else:
                    status = "WARN"
                    reason = reason or "no_rows_in_requested_window"
            except BinanceAPIError as exc:
                status = "FAIL"
                reason = exc.reason or "api_error"
                failures.append(f"{symbol}:{metric}:{reason}")

            row = compose_coverage_row(
                repo_root=repo_root,
                symbol=symbol,
                metric=metric,
                existing_row=existing,
                source_earliest_utc=source_earliest,
                source_latest_utc=source_latest,
                status=status,
                reason=reason,
            )
            updates.append(row)
            print(
                f"{symbol} {metric} status={row['status']} added={added_rows} "
                f"rows={row['rows']} earliest={row['earliest_utc']} latest={row['latest_utc']} "
                f"reason={row['reason']}"
            )

        if args.skip_liquidations_probe:
            continue

        existing_liq = find_coverage_row(coverage_rows, symbol, "liquidations")
        liquidations = probe_liquidations(symbol)
        liquidations_row = compose_coverage_row(
            repo_root=repo_root,
            symbol=symbol,
            metric="liquidations",
            existing_row=existing_liq,
            source_earliest_utc=liquidations.get("earliest_utc"),
            source_latest_utc=liquidations.get("latest_utc"),
            status=str(liquidations.get("status") or "UNKNOWN"),
            reason=str(liquidations.get("reason") or ""),
        )
        updates.append(liquidations_row)
        print(
            f"{symbol} liquidations status={liquidations_row['status']} "
            f"earliest={liquidations_row['earliest_utc']} latest={liquidations_row['latest_utc']} "
            f"reason={liquidations_row['reason']}"
        )

    upsert_coverage_rows(coverage_path, updates)
    print(f"coverage_path={coverage_path}")
    print(f"rolling_window={to_iso_utc(rolling_start)}..{to_iso_utc(now_dt)}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
