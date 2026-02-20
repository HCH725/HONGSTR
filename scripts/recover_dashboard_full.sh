#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LOG_FILE="/tmp/hongstr_recover_dashboard_full.log"
: > "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== recover_dashboard_full: start ($(date)) ==="
echo "repo=$REPO_ROOT"

bash scripts/one_click_dashboard.sh --start 2020-01-01 --end now --skip-benchmark --skip-walkforward

if ! bash scripts/check_data_coverage.sh; then
  echo "WARN: coverage check failed after one_click; running backfill/top-off recovery"
  bash scripts/backfill_1m_from_2020.sh
  bash scripts/check_data_coverage.sh
fi

if ! bash scripts/healthcheck_dashboard.sh; then
  echo "ERROR: healthcheck failed after one-click recovery"
  for log in /tmp/hongstr_streamlit_8501.log /tmp/hongstr_streamlit_8502.log; do
    if [[ -f "$log" ]]; then
      echo "=== tail $log ==="
      tail -n 120 "$log" || true
    fi
  done
  exit 1
fi

PORT="8501"
if ! lsof -nP -iTCP:8501 -sTCP:LISTEN >/dev/null 2>&1; then
  if lsof -nP -iTCP:8502 -sTCP:LISTEN >/dev/null 2>&1; then
    PORT="8502"
  fi
fi

echo "RECOVERY_OK=1"
echo "URL_127=http://127.0.0.1:${PORT}/"
echo "LOG_FILE=$LOG_FILE"
echo "=== recover_dashboard_full: done ($(date)) ==="
