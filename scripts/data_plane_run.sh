#!/usr/bin/env bash
set -euo pipefail
set +x

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if [[ -f "${REPO_ROOT}/scripts/load_env.sh" ]]; then
  # Load local env without echoing values so scheduled runs can reuse .env safely.
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/scripts/load_env.sh"
fi

PY_BIN="${PYTHON_BIN:-${PY:-python3}}"
if [[ "${PY_BIN}" != "python3" && ! -x "${PY_BIN}" ]]; then
  PY_BIN="python3"
fi

STEP_TIMEOUT_SEC="${DATA_PLANE_STEP_TIMEOUT_SEC:-45}"
if [[ ! "${STEP_TIMEOUT_SEC}" =~ ^[0-9]+$ ]] || [[ "${STEP_TIMEOUT_SEC}" -lt 1 ]]; then
  STEP_TIMEOUT_SEC=45
fi

WARN_COUNT=0

ts_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

run_soft_step() {
  local step_name="$1"
  shift

  local start_ts end_ts elapsed rc
  start_ts="$(date +%s)"
  rc=0

  printf '[START] %s ts=%s\n' "${step_name}" "$(ts_utc)"
  if run_with_timeout "${STEP_TIMEOUT_SEC}" "$@"; then
    rc=0
  else
    rc=$?
    WARN_COUNT=$((WARN_COUNT + 1))
    printf '[WARN] %s exit=%s ts=%s\n' "${step_name}" "${rc}" "$(ts_utc)"
  fi

  end_ts="$(date +%s)"
  elapsed=$((end_ts - start_ts))
  printf '[DONE] %s exit=%s duration_sec=%s ts=%s\n' "${step_name}" "${rc}" "${elapsed}" "$(ts_utc)"
}

run_with_timeout() {
  local timeout_sec="$1"
  shift

  local cmd_pid timer_pid timer_flag wait_rc
  timer_flag="$(mktemp "${TMPDIR:-/tmp}/hongstr_data_plane_timeout.XXXXXX")"
  rm -f "${timer_flag}"

  "$@" &
  cmd_pid=$!

  (
    sleep "${timeout_sec}"
    if kill -0 "${cmd_pid}" >/dev/null 2>&1; then
      : > "${timer_flag}"
      kill "${cmd_pid}" >/dev/null 2>&1 || true
    fi
  ) &
  timer_pid=$!

  wait_rc=0
  if wait "${cmd_pid}"; then
    wait_rc=0
  else
    wait_rc=$?
  fi

  kill "${timer_pid}" >/dev/null 2>&1 || true
  wait "${timer_pid}" >/dev/null 2>&1 || true

  if [[ -f "${timer_flag}" ]]; then
    rm -f "${timer_flag}"
    return 124
  fi
  rm -f "${timer_flag}"

  return "${wait_rc}"
}

run_hard_step() {
  local step_name="$1"
  shift

  local start_ts end_ts elapsed rc
  start_ts="$(date +%s)"
  rc=0

  printf '[START] %s ts=%s\n' "${step_name}" "$(ts_utc)"
  if "$@"; then
    rc=0
  else
    rc=$?
    end_ts="$(date +%s)"
    elapsed=$((end_ts - start_ts))
    printf '[FAIL] %s exit=%s duration_sec=%s ts=%s\n' "${step_name}" "${rc}" "${elapsed}" "$(ts_utc)"
    return "${rc}"
  fi

  end_ts="$(date +%s)"
  elapsed=$((end_ts - start_ts))
  printf '[DONE] %s exit=%s duration_sec=%s ts=%s\n' "${step_name}" "${rc}" "${elapsed}" "$(ts_utc)"
}

main() {
  run_soft_step "futures_metrics_daily" "${PY_BIN}" scripts/futures_metrics_daily.py
  run_soft_step "okx_public_fetch" "${PY_BIN}" scripts/okx_public_fetch.py
  run_soft_step "bitfinex_public_fetch" "${PY_BIN}" scripts/bitfinex_public_fetch.py
  run_soft_step "cmc_market_intel_fetch" "${PY_BIN}" scripts/cmc_market_intel_fetch.py

  run_hard_step "refresh_state" bash scripts/refresh_state.sh

  printf '[SUMMARY] data_plane warnings=%s ts=%s\n' "${WARN_COUNT}" "$(ts_utc)"
}

main "$@"
