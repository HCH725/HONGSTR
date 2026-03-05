#!/usr/bin/env bash
set -euo pipefail

readonly JOB_LABEL="com.hongstr.obsidian_mirror"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
readonly DEFAULT_PRIMARY_ROOT_REL="_local/obsidian_vault"
readonly DEFAULT_ICLOUD_OBSIDIAN_ROOT="${HOME}/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian"
readonly DEFAULT_ICLOUD_VAULT_NAME="HONGSTR_MIRROR"
readonly DEFAULT_MIRROR_ENABLED="1"
readonly DEFAULT_LOCK_DIR="/tmp/${JOB_LABEL}.lock"

export PATH="${DEFAULT_PATH}"

LOCK_ACQUIRED=0
LOCK_DIR="${OBSIDIAN_MIRROR_LOCK_DIR:-${DEFAULT_LOCK_DIR}}"

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

resolve_source_vault() {
  local primary_root="$1"
  if [[ -d "${primary_root}/HONGSTR" ]]; then
    printf '%s\n' "${primary_root}/HONGSTR"
    return 0
  fi
  if [[ -d "${primary_root}" && "$(basename "${primary_root}")" == "HONGSTR" ]]; then
    printf '%s\n' "${primary_root}"
    return 0
  fi
  return 1
}

sync_dir() {
  local source_vault="$1"
  local target_vault="$2"
  local rel="$3"
  local strict_mirror="$4"
  local dry_run="$5"
  local src="${source_vault}/${rel}"
  local dst="${target_vault}/${rel}"
  local -a rsync_opts
  local -a rsync_dry_run_flags
  rsync_opts=(
    --archive
    --human-readable
    --exclude ".DS_Store"
    --exclude ".obsidian/workspace*"
    --exclude ".obsidian/cache/"
    --exclude ".obsidian/*history*"
    --exclude "raw/***"
    --exclude "*/raw/***"
    --exclude "state/***"
    --exclude "*/state/***"
    --exclude "cache/***"
    --exclude "*/cache/***"
    --exclude "db/***"
    --exclude "*/db/***"
    --exclude "*.parquet"
    --exclude "*.pkl"
    --exclude "*.pickle"
    --exclude "*.joblib"
  )
  if [[ "${dry_run}" == "1" ]]; then
    rsync_dry_run_flags=(--dry-run --itemize-changes)
  else
    rsync_dry_run_flags=(--itemize-changes)
  fi

  if [[ ! -d "${src}" ]]; then
    log_warn "source_missing rel=${rel} source=${src}"
    return 10
  fi

  if ! mkdir -p "${dst}"; then
    log_warn "mkdir_failed rel=${rel} target=${dst}"
    return 11
  fi

  if [[ "${strict_mirror}" == "1" ]]; then
    if rsync "${rsync_opts[@]}" "${rsync_dry_run_flags[@]}" --delete --delete-excluded "${src}/" "${dst}/"; then
      log_info "synced rel=${rel} source=${src} target=${dst}"
      return 0
    fi
  else
    if rsync "${rsync_opts[@]}" "${rsync_dry_run_flags[@]}" "${src}/" "${dst}/"; then
      log_info "synced rel=${rel} source=${src} target=${dst}"
      return 0
    fi
  fi

  log_warn "rsync_failed rel=${rel} source=${src} target=${dst}"
  return 12
}

main() {
  local repo_root mirror_enabled primary_root source_vault
  local icloud_root vault_name target_vault
  local -a include_dirs
  local synced_count=0
  local missing_count=0
  local strict_mirror
  local dry_run
  local delete_mode
  local run_mode

  mirror_enabled="${MIRROR_ENABLED:-${DEFAULT_MIRROR_ENABLED}}"
  if [[ "${mirror_enabled}" != "1" ]]; then
    log_info "disabled MIRROR_ENABLED=${mirror_enabled}"
    return 0
  fi

  strict_mirror="${STRICT_MIRROR:-0}"
  if [[ "${strict_mirror}" != "1" ]]; then
    strict_mirror="0"
  fi

  dry_run="${DRY_RUN:-0}"
  if [[ "${dry_run}" != "1" ]]; then
    dry_run="0"
  fi

  if ! command -v rsync >/dev/null 2>&1; then
    log_warn "rsync_not_found action=skip"
    return 0
  fi

  repo_root="$(resolve_repo_root)"
  primary_root="${OBSIDIAN_PRIMARY_ROOT:-${repo_root}/${DEFAULT_PRIMARY_ROOT_REL}}"
  if ! source_vault="$(resolve_source_vault "${primary_root}")"; then
    log_warn "primary_vault_not_found OBSIDIAN_PRIMARY_ROOT=${primary_root}"
    return 0
  fi

  icloud_root="${ICLOUD_OBSIDIAN_ROOT:-${DEFAULT_ICLOUD_OBSIDIAN_ROOT}}"
  vault_name="${ICLOUD_VAULT_NAME:-${DEFAULT_ICLOUD_VAULT_NAME}}"
  target_vault="${icloud_root}/${vault_name}"
  include_dirs=(KB Dashboards)

  if ! mkdir -p "${target_vault}"; then
    log_warn "target_vault_not_accessible target=${target_vault}"
    return 0
  fi

  if ! acquire_lock; then
    return 0
  fi

  if [[ "${strict_mirror}" == "1" ]]; then
    delete_mode="strict"
  else
    delete_mode="disabled"
  fi

  if [[ "${dry_run}" == "1" ]]; then
    run_mode="dry_run"
  else
    run_mode="apply"
  fi

  log_info "start source_vault=${source_vault} target_vault=${target_vault} includes=${include_dirs[*]} strict_mirror=${strict_mirror} dry_run=${dry_run}"
  for rel in "${include_dirs[@]}"; do
    if sync_dir "${source_vault}" "${target_vault}" "${rel}" "${strict_mirror}" "${dry_run}"; then
      ((synced_count += 1))
    else
      rc="$?"
      if [[ "${rc}" == "10" ]]; then
        ((missing_count += 1))
      fi
    fi
  done

  log_info "done synced_dirs=${synced_count} missing_dirs=${missing_count} delete_mode=${delete_mode} run_mode=${run_mode} retention=permanent"
  return 0
}

main "$@"
