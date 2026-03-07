#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
source "${REPO_ROOT}/scripts/load_env.sh"

RUN_LOG="/tmp/hongstr_weekly_backfill_$(date +%Y%m%d_%H%M%S).log"
if ! exec > >(tee -a "$RUN_LOG") 2>&1; then
  echo "WARN: tee logging unavailable; falling back to file-only log at $RUN_LOG" >&2
  exec >>"$RUN_LOG" 2>&1
fi

PY="${PY:-$REPO_ROOT/.venv/bin/python}"
if [[ ! -x "$PY" ]]; then
  echo "ERROR: venv python not found: $PY" >&2
  exit 1
fi

SYMBOLS="${SYMBOLS:-BTCUSDT ETHUSDT BNBUSDT}"
START_DATE="${START_DATE:-2020-01-01}"
END_DATE="${END_DATE:-now}"
USE_CP_REPORTS="${HONGSTR_USE_CONTROL_PLANE_REPORTS:-0}"
LATEST_SUMMARY="(not available)"
script_status="running"

notify() {
  bash scripts/notify_telegram.sh "$@" || true
}

run_control_plane() {
  if [[ -x "$REPO_ROOT/scripts/control_plane_report.sh" ]]; then
    bash "$REPO_ROOT/scripts/control_plane_report.sh" || true
  elif [[ -x "$REPO_ROOT/scripts/control_plane_run.sh" ]]; then
    bash "$REPO_ROOT/scripts/control_plane_run.sh" || true
  fi
}

on_exit() {
  local rc=$?
  run_control_plane
  if [[ "$rc" -eq 0 ]]; then
    if [[ "$script_status" == "success" ]]; then
      notify \
        --status ok \
        --title "WEEKLY BACKFILL OK" \
        --body "symbols=$SYMBOLS start=$START_DATE end=$END_DATE\n$LATEST_SUMMARY"
    fi
    exit 0
  fi

  notify \
    --status fail \
    --title "WEEKLY BACKFILL FAIL" \
    --body "symbols=$SYMBOLS start=$START_DATE end=$END_DATE\nlog=$RUN_LOG"
  notify \
    --status fail \
    --title "WEEKLY BACKFILL FAIL LOG TAIL" \
    --body "tail -n 60 attached\nlog=$RUN_LOG" \
    --log-tail "$RUN_LOG" \
    --tail-lines 60
  exit "$rc"
}
trap on_exit EXIT

echo "=== BACKFILL 1m from $START_DATE to $END_DATE ==="
echo "PY=$PY"
"$PY" - <<'PY'
import ssl
print("PYTHON_OK:", ssl.OPENSSL_VERSION)
PY

for sym in $SYMBOLS; do
  echo ">> Backfill $sym 1m: $START_DATE -> $END_DATE"
  "$PY" scripts/ingest_historical.py --symbol "$sym" --tf "1m" --start "$START_DATE" --end "$END_DATE"
  echo ">> Aggregate $sym from 1m source"
  "$PY" scripts/aggregate_data.py --symbol "$sym"
done

set +e
coverage_out="$(bash scripts/check_data_coverage.sh 2>&1)"
coverage_rc=$?
set -e

coverage_summary="$(echo "$coverage_out" | awk '/^BTCUSDT|^ETHUSDT|^BNBUSDT|^OVERALL_STATUS/' || true)"
if [[ "$USE_CP_REPORTS" == "1" ]]; then
  echo "INFO: coverage gate executed via scripts/check_data_coverage.sh"
  echo "INFO: full coverage table delegated to control-plane/event reports"
  if [[ -n "$coverage_summary" ]]; then
    echo "$coverage_summary"
  fi
else
  echo "$coverage_out"
fi
LATEST_SUMMARY="$coverage_summary"
if [[ -z "$LATEST_SUMMARY" ]]; then
  LATEST_SUMMARY="coverage output unavailable"
fi

if [[ "$coverage_rc" -ne 0 ]]; then
  echo "ERROR: coverage check failed during backfill" >&2
  exit "$coverage_rc"
fi

echo "=== BACKFILL COMPLETE ==="
script_status="success"
