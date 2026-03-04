#!/usr/bin/env bash
# obsidian_daily_run.sh – SSOT daily exporter → LanceDB incremental index
# Runs hourly under com.hongstr.obsidian_daily launchd job.
# Pattern mirrors obsidian_rag_run.sh.
set -euo pipefail

readonly JOB_LABEL="com.hongstr.obsidian_daily"
readonly OLLAMA_URL="http://127.0.0.1:11434/api/embeddings"
readonly OLLAMA_MODEL="nomic-embed-text"
readonly DEFAULT_PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

export PATH="${DEFAULT_PATH}"

LOCK_DIR=""
PROVIDER="fallback"
declare -a PROVIDER_ARGS=()

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

release_lock() {
  if [[ -n "${LOCK_DIR}" && -d "${LOCK_DIR}" ]]; then
    rm -f "${LOCK_DIR}/pid" 2>/dev/null || true
    rmdir "${LOCK_DIR}" 2>/dev/null || true
  fi
}

warn_exit() {
  local rc="$1" stage="$2"
  echo "WARN ${JOB_LABEL}: stage=${stage} rc=${rc} end_utc=$(now_utc)" >&2
  if [[ "${OBSIDIAN_DAILY_STRICT:-0}" == "1" ]]; then return "${rc}"; fi
  return 0
}

acquire_lock() {
  local lock_dir="${OBSIDIAN_DAILY_LOCK_DIR:-/tmp/${JOB_LABEL}.lock}"
  if mkdir "${lock_dir}" 2>/dev/null; then
    LOCK_DIR="${lock_dir}"
    printf '%s\n' "$$" > "${LOCK_DIR}/pid"
    trap release_lock EXIT INT TERM HUP
    return 0
  fi
  if [[ -d "${lock_dir}" ]]; then
    echo "WARN ${JOB_LABEL}: stage=lock_exists lock_dir=${lock_dir} end_utc=$(now_utc)" >&2
    return 2
  fi
  return 1
}

detect_provider() {
  local payload
  payload=$(printf '{"model":"%s","prompt":"%s"}' "${OLLAMA_MODEL}" "hongstr obsidian daily healthcheck")
  if curl -fsS --max-time 5 -H "Content-Type: application/json" -d "${payload}" "${OLLAMA_URL}" >/dev/null 2>&1; then
    PROVIDER="ollama"
    PROVIDER_ARGS=(--provider ollama --ollama-model "${OLLAMA_MODEL}")
    return 0
  fi
  PROVIDER="fallback"
  PROVIDER_ARGS=(--provider fallback)
  return 0
}

run_job() {
  local start_utc repo_root log_dir python_bin exporter_script index_script rc
  start_utc="$(now_utc)"

  if ! repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    rc=$?; warn_exit "${rc}" "git_rev_parse"; return "$?"
  fi
  cd "${repo_root}"

  log_dir="${HOME}/Library/Logs/hongstr"
  mkdir -p "${log_dir}" || { rc=$?; warn_exit "${rc}" "mkdir_log_dir"; return "$?"; }

  if ! acquire_lock; then
    rc=$?
    [[ "${rc}" == "2" ]] && return 0   # already running – not an error
    warn_exit "${rc}" "lock_acquire"; return "$?"
  fi

  # ── Load .env if present ──────────────────────────────────────────────────
  if [[ -f "${repo_root}/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${repo_root}/.env"
    set +a
  fi

  # ── Locate python ─────────────────────────────────────────────────────────
  python_bin="${repo_root}/.venv/bin/python"
  if [[ ! -x "${python_bin}" ]]; then
    python_bin="$(command -v python3 2>/dev/null || true)"
  fi
  if [[ -z "${python_bin}" || ! -x "${python_bin}" ]]; then
    warn_exit 127 "python_missing"; return "$?"
  fi

  exporter_script="${repo_root}/scripts/obsidian_ssot_daily.py"
  index_script="${repo_root}/scripts/obsidian_lancedb_index.py"

  # ── Step 1: SSOT → KB daily note ─────────────────────────────────────────
  if ! "${python_bin}" "${exporter_script}" --repo-root "${repo_root}"; then
    rc=$?; warn_exit "${rc}" "ssot_daily_export"; return "$?"
  fi

  # ── Step 2: Detect Ollama → LanceDB incremental index ────────────────────
  detect_provider

  if ! "${python_bin}" "${index_script}" --incremental "${PROVIDER_ARGS[@]}"; then
    rc=$?; warn_exit "${rc}" "lancedb_index"; return "$?"
  fi

  echo "OK ${JOB_LABEL}: start_utc=${start_utc} end_utc=$(now_utc) provider=${PROVIDER}"
  return 0
}

main() {
  if run_job; then return 0; else return "$?"; fi
}

main "$@"
