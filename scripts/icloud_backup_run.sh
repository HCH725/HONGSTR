#!/usr/bin/env bash
set -u
set -o pipefail

readonly JOB_LABEL="com.hongstr.icloud_backup"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
readonly DEFAULT_BACKUP_ENABLED="1"
readonly DEFAULT_BACKUP_MODE="full"
readonly DEFAULT_BACKUP_ROOT="${HOME}/Library/Mobile Documents/com~apple~CloudDocs/HONGSTR_BACKUP"
readonly DEFAULT_BACKUP_RETENTION_DAYS="0"
readonly DEFAULT_BACKUP_DRY_RUN="0"

export PATH="${DEFAULT_PATH}"
declare -a EXCLUDE_PATTERNS=()
SYNC_RESULT_SYNCED=0
SYNC_RESULT_MISSING=0
SYNC_RESULT_ERRORS=0

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

snapshot_date_utc() {
  date -u +"%Y-%m-%d"
}

log_info() {
  printf 'INFO %s: %s ts_utc=%s\n' "${JOB_LABEL}" "$*" "$(now_utc)"
}

log_warn() {
  printf 'WARN %s: %s ts_utc=%s\n' "${JOB_LABEL}" "$*" "$(now_utc)" >&2
}

resolve_repo_root() {
  if [[ -n "${HONGSTR_REPO_ROOT:-}" && -d "${HONGSTR_REPO_ROOT}" ]]; then
    printf '%s\n' "${HONGSTR_REPO_ROOT}"
    return 0
  fi
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    git rev-parse --show-toplevel
    return 0
  fi
  pwd
}

is_int() {
  [[ "$1" =~ ^-?[0-9]+$ ]]
}

join_csv() {
  local out=""
  local item
  for item in "$@"; do
    if [[ -z "${out}" ]]; then
      out="${item}"
    else
      out="${out},${item}"
    fi
  done
  printf '%s\n' "${out}"
}

count_target_files() {
  local target_root="$1"
  if [[ ! -d "${target_root}" ]]; then
    printf '0\n'
    return 0
  fi
  find "${target_root}" -type f | wc -l | tr -d ' '
}

count_target_bytes() {
  local target_root="$1"
  if [[ ! -d "${target_root}" ]]; then
    printf '0\n'
    return 0
  fi
  du -sk "${target_root}" 2>/dev/null | awk '{print $1 * 1024}'
}

write_manifest() {
  local target_root="$1"
  local ts_utc="$2"
  local mode="$3"
  local source_root="$4"
  local files_count="$5"
  local bytes_count="$6"
  local synced_count="$7"
  local missing_count="$8"
  local error_count="$9"
  shift 9
  local manifest_path="${target_root}/manifest.json"
  local manifest_tmp="${manifest_path}.tmp"
  if ! command -v python3 >/dev/null 2>&1; then
    log_warn "python3_not_found manifest_skip target=${target_root}"
    return 1
  fi
  if ! python3 - "${manifest_tmp}" "${ts_utc}" "${mode}" "${source_root}" "${target_root}" "${files_count}" "${bytes_count}" "${synced_count}" "${missing_count}" "${error_count}" "$@" <<'PY'
import json
import sys
from pathlib import Path

manifest_tmp = Path(sys.argv[1])
ts_utc = sys.argv[2]
mode = sys.argv[3]
source_root = sys.argv[4]
target_root = sys.argv[5]
files_count = int(sys.argv[6])
bytes_count = int(float(sys.argv[7]))
synced_count = int(sys.argv[8])
missing_count = int(sys.argv[9])
error_count = int(sys.argv[10])
excludes = list(sys.argv[11:])

payload = {
    "ts_utc": ts_utc,
    "mode": mode,
    "counts": {
        "files": files_count,
        "synced_paths": synced_count,
        "missing_sources": missing_count,
        "errors": error_count,
    },
    "bytes": bytes_count,
    "source_root": source_root,
    "target_root": target_root,
    "excludes_summary": excludes,
}
manifest_tmp.parent.mkdir(parents=True, exist_ok=True)
manifest_tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
  then
    log_warn "manifest_write_failed target=${target_root}"
    return 1
  fi
  if ! mv -f "${manifest_tmp}" "${manifest_path}"; then
    log_warn "manifest_move_failed target=${target_root}"
    return 1
  fi
  return 0
}

append_sha_for_file() {
  local file_path="$1"
  local out_file="$2"
  if ! shasum -a 256 "${file_path}" >> "${out_file}" 2>/dev/null; then
    log_warn "sha256_failed path=${file_path}"
    return 1
  fi
  return 0
}

write_sha256sums() {
  local target_root="$1"
  local ts_utc="$2"
  local mode="$3"
  local out_path="${target_root}/sha256sums.txt"
  local out_tmp="${out_path}.tmp"
  local f key_dir
  local -a key_dirs
  key_dirs=(
    "scripts"
    "docs"
    "launchd"
    "web"
    "_local/obsidian_vault/HONGSTR/KB"
    "_local/obsidian_vault/HONGSTR/Dashboards"
    "data/state"
    "reports/state_atomic"
  )

  if ! command -v shasum >/dev/null 2>&1; then
    log_warn "shasum_not_found target=${target_root}"
    printf 'sha256 unavailable at ts_utc=%s mode=%s\n' "${ts_utc}" "${mode}" > "${out_tmp}"
    mv -f "${out_tmp}" "${out_path}" || true
    return 1
  fi

  printf '# ts_utc=%s mode=%s\n' "${ts_utc}" "${mode}" > "${out_tmp}"
  if [[ -f "${target_root}/manifest.json" ]]; then
    append_sha_for_file "${target_root}/manifest.json" "${out_tmp}" || true
  fi

  for key_dir in "${key_dirs[@]}"; do
    local dir_path="${target_root}/${key_dir}"
    if [[ ! -d "${dir_path}" ]]; then
      continue
    fi
    while IFS= read -r f; do
      if [[ -n "${f}" ]]; then
        append_sha_for_file "${f}" "${out_tmp}" || true
      fi
    done < <(
      find "${dir_path}" -type f -size -5M \( \
        -name "*.sh" -o -name "*.py" -o -name "*.md" -o -name "*.json" -o -name "*.plist" -o -name "*.txt" \
      \) | LC_ALL=C sort | head -n 300
    )
  done

  if ! mv -f "${out_tmp}" "${out_path}"; then
    log_warn "sha256_move_failed target=${target_root}"
    return 1
  fi
  return 0
}

sync_rel_path() {
  local source_root="$1"
  local target_root="$2"
  local rel_path="$3"
  local delete_mode="$4"
  local mode="$5"
  local dry_run="$6"
  shift 6
  local src="${source_root}/${rel_path}"
  local dst="${target_root}/${rel_path}"
  local rc
  local -a rsync_opts
  rsync_opts=(--archive --human-readable)
  if [[ "${dry_run}" == "1" ]]; then
    rsync_opts+=(-n)
  fi
  if [[ "${delete_mode}" == "1" ]]; then
    rsync_opts+=(--delete --delete-excluded)
  fi
  if [[ "${mode}" == "incremental" ]]; then
    rsync_opts+=(--update)
  fi
  rsync_opts+=("$@")

  if [[ ! -d "${src}" ]]; then
    log_warn "source_missing rel=${rel_path} source=${src}"
    return 10
  fi
  if ! mkdir -p "${dst}"; then
    log_warn "mkdir_failed rel=${rel_path} target=${dst}"
    return 11
  fi
  rsync "${rsync_opts[@]}" "${src}/" "${dst}/"
  rc=$?
  if [[ "${rc}" -ne 0 ]]; then
    log_warn "rsync_failed rel=${rel_path} source=${src} target=${dst} rc=${rc}"
    return 12
  fi
  log_info "synced rel=${rel_path} source=${src} target=${dst} dry_run=${dry_run}"
  return 0
}

sync_target() {
  local source_root="$1"
  local target_root="$2"
  local mode="$3"
  local delete_mode="$4"
  local dry_run="$5"
  shift 5
  local rel_path rc
  local synced_count=0
  local missing_count=0
  local error_count=0
  local -a allowlist_paths
  allowlist_paths=(
    "scripts"
    "docs"
    "launchd"
    "web"
    "_local/obsidian_vault/HONGSTR/KB"
    "_local/obsidian_vault/HONGSTR/Dashboards"
    "data/state"
    "reports/state_atomic"
    "data/derived"
    "data/backtests"
  )
  local -a exclude_args
  exclude_args=("$@")

  if ! mkdir -p "${target_root}"; then
    log_warn "target_not_accessible target=${target_root}"
    SYNC_RESULT_SYNCED="${synced_count}"
    SYNC_RESULT_MISSING="${missing_count}"
    SYNC_RESULT_ERRORS="$((error_count + 1))"
    return 0
  fi

  for rel_path in "${allowlist_paths[@]}"; do
    sync_rel_path "${source_root}" "${target_root}" "${rel_path}" "${delete_mode}" "${mode}" "${dry_run}" "${exclude_args[@]}"
    rc=$?
    if [[ "${rc}" -eq 0 ]]; then
      synced_count=$((synced_count + 1))
    elif [[ "${rc}" -eq 10 ]]; then
      missing_count=$((missing_count + 1))
    else
      error_count=$((error_count + 1))
    fi
  done

  if [[ "${dry_run}" != "1" ]]; then
    local ts_utc
    local files_count
    local bytes_count
    ts_utc="$(now_utc)"
    files_count="$(count_target_files "${target_root}")"
    bytes_count="$(count_target_bytes "${target_root}")"
    write_manifest "${target_root}" "${ts_utc}" "${mode}" "${source_root}" "${files_count}" "${bytes_count}" "${synced_count}" "${missing_count}" "${error_count}" "${EXCLUDE_PATTERNS[@]}" || error_count=$((error_count + 1))
    write_sha256sums "${target_root}" "${ts_utc}" "${mode}" || error_count=$((error_count + 1))
  fi

  SYNC_RESULT_SYNCED="${synced_count}"
  SYNC_RESULT_MISSING="${missing_count}"
  SYNC_RESULT_ERRORS="${error_count}"
  return 0
}

prune_snapshots() {
  local backup_root="$1"
  local retention_days="$2"
  local dry_run="$3"
  local snapshots_root="${backup_root}/snapshots"
  local old_dir

  if [[ "${retention_days}" -le 0 ]]; then
    return 0
  fi
  if [[ "${dry_run}" == "1" ]]; then
    log_info "retention_skip_dry_run days=${retention_days}"
    return 0
  fi
  if [[ ! -d "${snapshots_root}" ]]; then
    return 0
  fi

  while IFS= read -r old_dir; do
    if [[ -n "${old_dir}" ]]; then
      rm -rf "${old_dir}" || log_warn "retention_delete_failed path=${old_dir}"
      log_info "retention_deleted path=${old_dir}"
    fi
  done < <(find "${snapshots_root}" -mindepth 1 -maxdepth 1 -type d -mtime +"${retention_days}" | LC_ALL=C sort)
}

main() {
  local backup_enabled backup_mode backup_root retention_days dry_run
  local source_root latest_root snapshot_root snapshot_day
  local latest_synced latest_missing latest_errors
  local snap_synced snap_missing snap_errors
  local total_errors=0
  local -a exclude_args

  backup_enabled="${BACKUP_ENABLED:-${DEFAULT_BACKUP_ENABLED}}"
  if [[ "${backup_enabled}" != "1" ]]; then
    log_info "disabled BACKUP_ENABLED=${backup_enabled}"
    return 0
  fi

  backup_mode="${BACKUP_MODE:-${DEFAULT_BACKUP_MODE}}"
  if [[ "${backup_mode}" != "full" && "${backup_mode}" != "incremental" ]]; then
    log_warn "invalid_mode BACKUP_MODE=${backup_mode} fallback=full"
    backup_mode="full"
  fi

  backup_root="${BACKUP_ROOT:-${DEFAULT_BACKUP_ROOT}}"
  retention_days="${BACKUP_RETENTION_DAYS:-${DEFAULT_BACKUP_RETENTION_DAYS}}"
  dry_run="${BACKUP_DRY_RUN:-${DEFAULT_BACKUP_DRY_RUN}}"
  if ! is_int "${retention_days}"; then
    log_warn "invalid_retention BACKUP_RETENTION_DAYS=${retention_days} fallback=0"
    retention_days=0
  fi
  if [[ "${dry_run}" != "1" ]]; then
    dry_run="0"
  fi

  if ! command -v rsync >/dev/null 2>&1; then
    log_warn "rsync_not_found action=skip"
    return 0
  fi

  source_root="$(resolve_repo_root)"
  snapshot_day="$(snapshot_date_utc)"
  latest_root="${backup_root}/latest"
  snapshot_root="${backup_root}/snapshots/${snapshot_day}"

  EXCLUDE_PATTERNS=(
    ".git/"
    "node_modules/"
    ".venv/"
    "dist/"
    "__pycache__/"
    ".DS_Store"
    "*.parquet"
    "*.pkl"
    "*.pickle"
    ".env"
    ".env.*"
    "*token*"
    "*secret*"
    "*.key"
    "id_rsa"
    "id_rsa.pub"
    ".ssh/"
    "*keychain*"
    "*Keychain*"
    "*Browser*"
  )
  exclude_args=()
  for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    exclude_args+=(--exclude "${pattern}")
  done

  log_info "start mode=${backup_mode} dry_run=${dry_run} source_root=${source_root} backup_root=${backup_root}"
  sync_target "${source_root}" "${latest_root}" "${backup_mode}" "1" "${dry_run}" "${exclude_args[@]}"
  latest_synced="${SYNC_RESULT_SYNCED:-0}"
  latest_missing="${SYNC_RESULT_MISSING:-0}"
  latest_errors="${SYNC_RESULT_ERRORS:-0}"

  sync_target "${source_root}" "${snapshot_root}" "${backup_mode}" "0" "${dry_run}" "${exclude_args[@]}"
  snap_synced="${SYNC_RESULT_SYNCED:-0}"
  snap_missing="${SYNC_RESULT_MISSING:-0}"
  snap_errors="${SYNC_RESULT_ERRORS:-0}"

  total_errors=$((latest_errors + snap_errors))

  prune_snapshots "${backup_root}" "${retention_days}" "${dry_run}" || true

  log_info "done latest_synced=${latest_synced} latest_missing=${latest_missing} snapshot_synced=${snap_synced} snapshot_missing=${snap_missing} errors=${total_errors} excludes=$(join_csv "${EXCLUDE_PATTERNS[@]}")"
  if [[ "${total_errors}" -gt 0 ]]; then
    log_warn "backup_completed_with_warnings errors=${total_errors}"
  fi
  return 0
}

main "$@"
