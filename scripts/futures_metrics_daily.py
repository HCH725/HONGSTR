#!/usr/bin/env python3
"""
Daily rolling wrapper for Binance Futures metrics.

This keeps the data-plane entrypoint stable while reusing the existing rolling fetcher.
"""
from __future__ import annotations

import os
import sys

from futures_metrics_fetch import main as futures_metrics_fetch_main


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT")


def _days_arg() -> str:
    raw = str(os.environ.get("FUTURES_METRICS_DAYS", "7") or "7").strip()
    try:
        days = int(raw)
    except ValueError:
        days = 7
    return str(max(1, days))


def main() -> int:
    original_argv = sys.argv[:]
    sys.argv = [
        original_argv[0],
        "--symbols",
        *DEFAULT_SYMBOLS,
        "--days",
        _days_arg(),
        "--skip-probe",
        *original_argv[1:],
    ]
    try:
        return int(futures_metrics_fetch_main())
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    raise SystemExit(main())
