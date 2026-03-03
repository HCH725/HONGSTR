#!/usr/bin/env bash

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

PY="${PYTHON_BIN:-python3}"
DAYS="${FUTURES_METRICS_DAYS:-7}"

exec "$PY" scripts/futures_metrics_fetch.py \
  --symbols BTCUSDT ETHUSDT BNBUSDT \
  --days "$DAYS" \
  "$@"
