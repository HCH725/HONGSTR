#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LOG_FILE="/tmp/hongstr_recover_dashboard_full.log"
: > "$LOG_FILE"
if ! exec > >(tee -a "$LOG_FILE") 2>&1; then
  echo "WARN: tee logging unavailable; falling back to file-only log at $LOG_FILE" >&2
  exec >>"$LOG_FILE" 2>&1
fi

script_status="running"
active_port="8501"

notify() {
  bash scripts/notify_telegram.sh "$@" || true
}

on_exit() {
  local rc=$?
  if [[ "$rc" -eq 0 ]]; then
    if [[ "$script_status" == "success" ]]; then
      notify \
        --status ok \
        --title "RECOVERY OK" \
        --body "Dashboard recovered." \
        --link "http://127.0.0.1:${active_port}/"
    fi
    exit 0
  fi

  local tail_file="/tmp/hongstr_recover_fail_tail_$(date +%Y%m%d_%H%M%S).log"
  {
    echo "=== recover log tail ==="
    tail -n 80 "$LOG_FILE" 2>/dev/null || true
    echo
    echo "=== streamlit log tail ==="
    tail -n 120 /tmp/hongstr_streamlit_8501.log 2>/dev/null || true
    tail -n 120 /tmp/hongstr_streamlit_8502.log 2>/dev/null || true
  } > "$tail_file"

  notify \
    --status fail \
    --title "RECOVERY FAIL" \
    --body "recover_dashboard_full failed.\nlog=$LOG_FILE" \
    --file "$tail_file"
  exit "$rc"
}
trap on_exit EXIT

echo "=== recover_dashboard_full start ($(date)) ==="
bash scripts/one_click_dashboard.sh --start 2020-01-01 --end now --skip-benchmark --skip-walkforward
bash scripts/check_data_coverage.sh
bash scripts/healthcheck_dashboard.sh

if lsof -nP -iTCP:8501 -sTCP:LISTEN >/dev/null 2>&1; then
  active_port="8501"
elif lsof -nP -iTCP:8502 -sTCP:LISTEN >/dev/null 2>&1; then
  active_port="8502"
fi

echo "RECOVERY_OK=1"
echo "URL_127=http://127.0.0.1:${active_port}/"
echo "LOG_FILE=${LOG_FILE}"
echo "=== recover_dashboard_full done ($(date)) ==="
script_status="success"
