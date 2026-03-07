#!/usr/bin/env bash
set -euo pipefail

readonly JOB_LABEL="com.hongstr.obsidian_mirror"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
readonly DEFAULT_PRIMARY_ROOT_REL="_local/obsidian_vault"
readonly DEFAULT_ICLOUD_OBSIDIAN_ROOT="${HOME}/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian"
readonly DEFAULT_ICLOUD_VAULT_NAME="HONGSTR_MIRROR"
readonly DEFAULT_MIRROR_ENABLED="1"
readonly LOCK_DIR="/tmp/${JOB_LABEL}.lock"
readonly KB_ACTIVE_CONTRACT="KB/{_meta,PR,Runbooks,Incidents,Research-Summaries}"

export PATH="${DEFAULT_PATH}"

LOCK_ACQUIRED=0

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

warn_legacy_kb_ssot() {
  local source_vault="$1"
  local target_vault="$2"
  local legacy_source_dir="${source_vault}/KB/SSOT"
  local legacy_target_dir="${target_vault}/KB/SSOT"

  if [[ -d "${legacy_source_dir}" ]]; then
    log_warn "legacy_kb_ssot_present path=${legacy_source_dir} active_contract=${KB_ACTIVE_CONTRACT} publish_mode=excluded current_daily_contract=Daily/YYYY/MM authoritative=0"
  fi

  if [[ -d "${legacy_target_dir}" ]]; then
    log_warn "legacy_kb_ssot_target_present path=${legacy_target_dir} active_contract=${KB_ACTIVE_CONTRACT} refresh_mode=disabled delete_mode=disabled authoritative=0"
  fi
}

is_optional_rel() {
  case "$1" in
    KB/_meta|KB/PR|KB/Runbooks|KB/Incidents|KB/Research-Summaries)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

sync_dir() {
  local source_vault="$1"
  local target_vault="$2"
  local rel="$3"
  local src="${source_vault}/${rel}"
  local dst="${target_vault}/${rel}"
  local -a rsync_opts
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

  if [[ ! -d "${src}" ]]; then
    if is_optional_rel "${rel}"; then
      log_info "source_optional_missing rel=${rel} source=${src}"
      return 0
    fi
    log_warn "source_missing rel=${rel} source=${src}"
    return 10
  fi

  if ! mkdir -p "${dst}"; then
    log_warn "mkdir_failed rel=${rel} target=${dst}"
    return 11
  fi

  if rsync "${rsync_opts[@]}" "${src}/" "${dst}/"; then
    log_info "synced rel=${rel} source=${src} target=${dst}"
    return 0
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

  mirror_enabled="${MIRROR_ENABLED:-${DEFAULT_MIRROR_ENABLED}}"
  if [[ "${mirror_enabled}" != "1" ]]; then
    log_info "disabled MIRROR_ENABLED=${mirror_enabled}"
    return 0
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
  include_dirs=(KB/_meta KB/PR KB/Runbooks KB/Incidents KB/Research-Summaries Dashboards Daily)

  if ! mkdir -p "${target_vault}"; then
    log_warn "target_vault_not_accessible target=${target_vault}"
    return 0
  fi
  warn_legacy_kb_ssot "${source_vault}" "${target_vault}"

  if ! acquire_lock; then
    return 0
  fi

  log_info "start source_vault=${source_vault} target_vault=${target_vault} includes=${include_dirs[*]} kb_contract=${KB_ACTIVE_CONTRACT} legacy_contract=KB/SSOT:frozen"
  for rel in "${include_dirs[@]}"; do
    if sync_dir "${source_vault}" "${target_vault}" "${rel}"; then
      ((synced_count += 1))
    else
      rc="$?"
      if [[ "${rc}" == "10" ]]; then
        ((missing_count += 1))
      fi
    fi
  done

  log_info "done synced_dirs=${synced_count} missing_dirs=${missing_count} delete_mode=disabled retention=permanent"
  return 0
}

main "$@"
