#!/usr/bin/env bash
# kb_sync_run.sh – wrapper for kb_sync_github_prs.py
# Handles: repo-root auto-detection, lockfile, vault mkdir, log routing, status summary.
# Logs: ~/Library/Logs/hongstr/kb_sync.out.log + kb_sync.err.log
set -euo pipefail

readonly JOB_LABEL="com.hongstr.kb_sync"
readonly LOCK_DIR="/tmp/hongstr_kb_sync.lock"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

export PATH="${DEFAULT_PATH}"

LOCK_ACQUIRED=0

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

release_lock() {
  if [[ "${LOCK_ACQUIRED}" == "1" ]]; then
    rm -f "${LOCK_DIR}/pid" 2>/dev/null || true
    rmdir "${LOCK_DIR}" 2>/dev/null || true
  fi
}

acquire_lock() {
  if mkdir "${LOCK_DIR}" 2>/dev/null; then
    LOCK_ACQUIRED=1
    printf '%s\n' "$$" > "${LOCK_DIR}/pid"
    trap release_lock EXIT INT TERM HUP
    return 0
  fi
  echo "WARN ${JOB_LABEL}: lock already held at ${LOCK_DIR}, skipping run end_utc=$(now_utc)" >&2
  return 2
}

main() {
  local start_utc repo_root vault_root meta_dir log_dir python_bin sync_script result_json
  local written=0 skipped=0 status="FAIL"

  start_utc="$(now_utc)"

  # ── locate repo root ──────────────────────────────────────────────────────
  if ! repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    echo "FAIL ${JOB_LABEL}: git rev-parse failed end_utc=$(now_utc)" >&2
    return 1
  fi
  cd "${repo_root}"

  # ── log dir ───────────────────────────────────────────────────────────────
  log_dir="${HOME}/Library/Logs/hongstr"
  mkdir -p "${log_dir}"

  # ── lockfile ──────────────────────────────────────────────────────────────
  if ! acquire_lock; then
    return 0  # already running – not an error
  fi

  # ── load .env if present ──────────────────────────────────────────────────
  if [[ -f "${repo_root}/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${repo_root}/.env"
    set +a
  fi

  # ── vault dirs ────────────────────────────────────────────────────────────
  vault_root="${repo_root}/_local/obsidian_vault/HONGSTR"
  meta_dir="${vault_root}/KB/_meta"
  mkdir -p "${meta_dir}" "${vault_root}/KB/PR"

  # ── locate python ─────────────────────────────────────────────────────────
  python_bin="${repo_root}/.venv/bin/python"
  if [[ ! -x "${python_bin}" ]]; then
    python_bin="$(command -v python3 2>/dev/null || true)"
  fi
  if [[ -z "${python_bin}" || ! -x "${python_bin}" ]]; then
    echo "FAIL ${JOB_LABEL}: python not found end_utc=$(now_utc)" >&2
    return 1
  fi

  sync_script="${repo_root}/scripts/kb_sync_github_prs.py"

  # ── run poller ────────────────────────────────────────────────────────────
  if result_json="$("${python_bin}" "${sync_script}" --repo-root "${repo_root}" 2>&1)"; then
    # Parse written/skipped/status from JSON output
    written="$(echo "${result_json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('written',0))" 2>/dev/null || echo 0)"
    skipped="$(echo "${result_json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('skipped',0))" 2>/dev/null || echo 0)"
    status="$(echo "${result_json}"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','OK'))" 2>/dev/null || echo OK)"
  else
    rc="$?"
    echo "FAIL ${JOB_LABEL}: poller exited rc=${rc} end_utc=$(now_utc)" >&2
    echo "${result_json}" >&2
    status="FAIL"
  fi

  echo "${status} ${JOB_LABEL}: written=${written} skipped=${skipped} start_utc=${start_utc} end_utc=$(now_utc)"
}

main "$@"
