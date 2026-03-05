#!/usr/bin/env bash
set -euo pipefail

readonly JOB_LABEL="com.hongstr.obsidian_dashboards"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
readonly DEFAULT_ENABLED="1"
readonly DEFAULT_LOCK_DIR="/tmp/${JOB_LABEL}.lock"

export PATH="${DEFAULT_PATH}"

LOCK_ACQUIRED=0
LOCK_DIR="${OBSIDIAN_DASHBOARDS_LOCK_DIR:-${DEFAULT_LOCK_DIR}}"

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_info() {
  printf 'INFO %s: %s ts_utc=%s\n' "${JOB_LABEL}" "$*" "$(now_utc)"
}

log_warn() {
  printf 'WARN %s: %s ts_utc=%s\n' "${JOB_LABEL}" "$*" "$(now_utc)" >&2
}

release_lock() {
  if [[ "${LOCK_ACQUIRED}" == "1" ]]; then
    rm -f "${LOCK_DIR}/pid" 2>/dev/null || true
    rmdir "${LOCK_DIR}" 2>/dev/null || true
    LOCK_ACQUIRED=0
  fi
}

acquire_lock() {
  if mkdir "${LOCK_DIR}" 2>/dev/null; then
    LOCK_ACQUIRED=1
    printf '%s\n' "$$" > "${LOCK_DIR}/pid"
    trap release_lock EXIT INT TERM HUP
    return 0
  fi
  log_warn "lock_exists lock_dir=${LOCK_DIR} action=skip"
  return 1
}

resolve_repo_root() {
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    git rev-parse --show-toplevel
    return 0
  fi
  pwd
}

main() {
  local enabled repo_root python_bin exporter_script

  enabled="${DASHBOARDS_EXPORT_ENABLED:-${DEFAULT_ENABLED}}"
  if [[ "${enabled}" != "1" ]]; then
    log_info "disabled DASHBOARDS_EXPORT_ENABLED=${enabled}"
    return 0
  fi

  if ! acquire_lock; then
    return 0
  fi

  repo_root="$(resolve_repo_root)"
  python_bin="${repo_root}/.venv/bin/python"
  if [[ ! -x "${python_bin}" ]]; then
    python_bin="$(command -v python3 2>/dev/null || true)"
  fi
  if [[ -z "${python_bin}" || ! -x "${python_bin}" ]]; then
    log_warn "python_not_found action=skip"
    return 0
  fi

  exporter_script="${repo_root}/scripts/obsidian_dashboards_export.py"
  if [[ ! -f "${exporter_script}" ]]; then
    log_warn "exporter_missing path=${exporter_script}"
    return 0
  fi

  if HONGSTR_REPO_ROOT="${repo_root}" "${python_bin}" "${exporter_script}"; then
    log_info "export_complete repo_root=${repo_root}"
    return 0
  fi

  rc="$?"
  log_warn "export_failed rc=${rc}"
  return 0
}

main "$@"
