#!/usr/bin/env bash
set -euo pipefail

readonly JOB_LABEL="com.hongstr.obsidian_mirror_run"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
readonly DEFAULT_DASHBOARDS_EXPORT_ENABLED="1"

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

resolve_repo_root() {
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    git rev-parse --show-toplevel
    return 0
  fi
  pwd
}

run_exporter() {
  local exporter_script="$1"
  if [[ ! -f "${exporter_script}" ]]; then
    log_warn "exporter_missing path=${exporter_script}"
    return 0
  fi
  if bash "${exporter_script}"; then
    log_info "exporter_done path=${exporter_script}"
    return 0
  fi
  rc="$?"
  log_warn "exporter_failed path=${exporter_script} rc=${rc}"
  return 0
}

run_mirror() {
  local mirror_script="$1"
  if [[ ! -f "${mirror_script}" ]]; then
    log_warn "mirror_missing path=${mirror_script}"
    return 0
  fi
  if bash "${mirror_script}"; then
    log_info "mirror_done path=${mirror_script}"
    return 0
  fi
  rc="$?"
  log_warn "mirror_failed path=${mirror_script} rc=${rc}"
  return 0
}

main() {
  local repo_root dashboards_export_enabled exporter_script mirror_script
  repo_root="$(resolve_repo_root)"

  dashboards_export_enabled="${DASHBOARDS_EXPORT_ENABLED:-${DEFAULT_DASHBOARDS_EXPORT_ENABLED}}"
  exporter_script="${OBSIDIAN_DASHBOARDS_EXPORT_SCRIPT:-${repo_root}/scripts/obsidian_dashboards_export.sh}"
  mirror_script="${OBSIDIAN_MIRROR_PUBLISH_SCRIPT:-${repo_root}/scripts/obsidian_mirror_publish.sh}"

  if [[ "${dashboards_export_enabled}" == "1" ]]; then
    run_exporter "${exporter_script}"
  else
    log_info "exporter_skipped DASHBOARDS_EXPORT_ENABLED=${dashboards_export_enabled}"
  fi

  run_mirror "${mirror_script}"
  log_info "pipeline_done repo_root=${repo_root}"
  return 0
}

main "$@"
