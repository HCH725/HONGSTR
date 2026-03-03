#!/usr/bin/env python3
"""
Chunked Binance Futures backfill with resumable checkpoints.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from futures_metrics_lib import (
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_COVERAGE_PATH,
    DEFAULT_SYMBOLS,
    DEFAULT_TARGET_START,
    HISTORICAL_METRICS,
    BinanceAPIError,
    build_windows,
    compose_coverage_row,
    find_coverage_row,
    iso_to_datetime,
    load_checkpoint,
    load_coverage_rows,
    next_window_start,
    parse_date_floor,
    probe_earliest_available,
    save_checkpoint,
    to_iso_utc,
    update_checkpoint_entry,
    upsert_coverage_rows,
    utc_now,
    write_metric_rows,
    fetch_metric_range,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Binance Futures metrics with checkpoint resume.")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--metrics", nargs="+", default=list(HISTORICAL_METRICS))
    parser.add_argument("--start-date", default=DEFAULT_TARGET_START)
    parser.add_argument("--end-date", default="now")
    parser.add_argument("--chunk-days", type=int, default=7)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--probe-step-days", type=int, default=31)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--coverage-path", default=str(DEFAULT_COVERAGE_PATH))
    parser.add_argument("--checkpoint-path", default=str(DEFAULT_CHECKPOINT_PATH))
    return parser.parse_args()


def _parse_end_date(raw_value: str):
    value = str(raw_value or "").strip().lower()
    if value in {"", "now"}:
        return utc_now()
    return parse_date_floor(raw_value)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    coverage_path = repo_root / args.coverage_path
    checkpoint_path = repo_root / args.checkpoint_path
    requested_start = parse_date_floor(args.start_date)
    requested_end = _parse_end_date(args.end_date)
    coverage_rows = load_coverage_rows(coverage_path)
    checkpoint_payload = load_checkpoint(checkpoint_path)
    updates: list[dict] = []
    failures: list[str] = []

    for symbol in args.symbols:
        for metric in args.metrics:
            existing = find_coverage_row(coverage_rows, symbol, metric)
            source_earliest = str((existing or {}).get("earliest_utc") or "").strip() or None
            status = "OK"
            reason = ""

            if not source_earliest:
                try:
                    probe = probe_earliest_available(
                        metric=metric,
                        symbol=symbol,
                        start_dt=requested_start,
                        now_dt=requested_end,
                        probe_step_days=args.probe_step_days,
                    )
                    source_earliest = probe.get("earliest_utc") or None
                    if probe.get("status") == "FAIL":
                        status = "FAIL"
                        reason = str(probe.get("reason") or "probe_failed")
                    elif probe.get("status") == "WARN":
                        status = "WARN"
                        reason = str(probe.get("reason") or "probe_warn")
                except BinanceAPIError as exc:
                    status = "FAIL"
                    reason = exc.reason or "probe_failed"

            if status == "FAIL":
                failures.append(f"{symbol}:{metric}:{reason}")
                updates.append(
                    compose_coverage_row(
                        repo_root=repo_root,
                        symbol=symbol,
                        metric=metric,
                        existing_row=existing,
                        source_earliest_utc=source_earliest,
                        status=status,
                        reason=reason,
                    )
                )
                continue

            effective_start = requested_start
            if source_earliest:
                effective_start = max(requested_start, iso_to_datetime(source_earliest))

            resume_start = next_window_start(
                checkpoint_payload=checkpoint_payload,
                symbol=symbol,
                metric=metric,
                default_start=effective_start,
            )
            windows = build_windows(resume_start, requested_end, args.chunk_days)
            if args.max_windows > 0:
                windows = windows[: args.max_windows]

            total_added = 0
            for window_start, window_end in windows:
                try:
                    rows = fetch_metric_range(metric, symbol, window_start, window_end)
                except BinanceAPIError as exc:
                    status = "FAIL"
                    reason = exc.reason or "api_error"
                    failures.append(f"{symbol}:{metric}:{reason}")
                    break

                if not rows:
                    status = "WARN"
                    reason = "no_rows_in_window"
                total_added += write_metric_rows(repo_root, symbol, metric, rows)
                update_checkpoint_entry(
                    checkpoint_payload=checkpoint_payload,
                    symbol=symbol,
                    metric=metric,
                    next_start=window_end,
                    last_end=window_end,
                )
                print(
                    f"{symbol} {metric} window={to_iso_utc(window_start)}..{to_iso_utc(window_end)} "
                    f"added={len(rows)}"
                )

            if not windows:
                reason = reason or "up_to_date"

            row = compose_coverage_row(
                repo_root=repo_root,
                symbol=symbol,
                metric=metric,
                existing_row=existing,
                source_earliest_utc=source_earliest,
                source_latest_utc=None,
                status=status,
                reason=reason,
            )
            checkpoint_entry = checkpoint_payload.get("checkpoints", {}).get(
                f"{symbol}::{metric}::{row['period']}",
                {},
            )
            updates.append(row)
            print(
                f"{symbol} {metric} status={row['status']} total_added={total_added} "
                f"rows={row['rows']} earliest={row['earliest_utc']} latest={row['latest_utc']} "
                f"next_start={checkpoint_entry.get('next_start_utc')}"
            )

    upsert_coverage_rows(coverage_path, updates)
    save_checkpoint(checkpoint_path, checkpoint_payload)
    print(f"coverage_path={coverage_path}")
    print(f"checkpoint_path={checkpoint_path}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
