#!/usr/bin/env bash
set -euo pipefail

readonly JOB_LABEL="com.hongstr.disable_noisy_jobs"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
readonly UID_VALUE="$(id -u)"

export PATH="${DEFAULT_PATH}"

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_info() {
  printf 'INFO %s: %s ts_utc=%s\n' "${JOB_LABEL}" "$*" "$(now_utc)"
}

log_warn() {
  printf 'WARN %s: %s ts_utc=%s\n' "${JOB_LABEL}" "$*" "$(now_utc)" >&2
}

print_disabled_state() {
  local label="$1"
  local disabled_output="$2"
  if printf '%s\n' "${disabled_output}" | grep -Eq "^[[:space:]]*\"${label}\"[[:space:]]*=>[[:space:]]*(disabled|true)\\b"; then
    log_info "disabled_confirmed label=${label}"
    return 0
  fi
  if printf '%s\n' "${disabled_output}" | grep -Eq "^[[:space:]]*\"${label}\"[[:space:]]*=>[[:space:]]*(enabled|false)\\b"; then
    log_warn "disabled_not_effective label=${label}"
    return 0
  fi
  log_warn "disabled_missing label=${label}"
  return 0
}

disable_job() {
  local label="$1"
  local target="gui/${UID_VALUE}/${label}"
  if launchctl bootout "${target}" >/dev/null 2>&1; then
    log_info "bootout_ok label=${label}"
  else
    log_info "bootout_skip label=${label}"
  fi
  if launchctl disable "${target}" >/dev/null 2>&1; then
    log_info "disable_ok label=${label}"
  else
    log_warn "disable_failed label=${label}"
  fi
}

main() {
  local -a labels
  local disabled_output
  labels=(
    "com.hongstr.obsidian_daily"
    "com.hongstr.kb_sync"
  )

  if ! command -v launchctl >/dev/null 2>&1; then
    log_warn "launchctl_not_found action=skip"
    return 0
  fi

  for label in "${labels[@]}"; do
    disable_job "${label}"
  done

  disabled_output="$(launchctl print-disabled "gui/${UID_VALUE}" 2>/dev/null || true)"
  for label in "${labels[@]}"; do
    print_disabled_state "${label}" "${disabled_output}"
  done

  return 0
}

main "$@"
