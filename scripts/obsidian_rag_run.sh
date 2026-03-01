#!/usr/bin/env bash
set -euo pipefail

readonly JOB_LABEL="com.hongstr.obsidian_rag"
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
  local rc="$1"
  local stage="$2"
  echo "WARN ${JOB_LABEL}: stage=${stage} rc=${rc} end_utc=$(now_utc)" >&2
  if [[ "${OBSIDIAN_RAG_STRICT:-0}" == "1" ]]; then
    return "${rc}"
  fi
  return 0
}

acquire_lock() {
  local lock_dir="${OBSIDIAN_RAG_LOCK_DIR:-/tmp/${JOB_LABEL}.lock}"
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
  payload=$(printf '{"model":"%s","prompt":"%s"}' "${OLLAMA_MODEL}" "hongstr obsidian rag healthcheck")
  if curl -fsS --max-time 5 -H "Content-Type: application/json" -d "${payload}" "${OLLAMA_URL}" >/dev/null; then
    PROVIDER="ollama"
    PROVIDER_ARGS=(--provider ollama --ollama-model "${OLLAMA_MODEL}")
    return 0
  fi
  PROVIDER="fallback"
  PROVIDER_ARGS=(--provider fallback)
  return 0
}

run_job() {
  local start_utc repo_root log_dir python_bin sync_script index_script rc
  start_utc="$(now_utc)"

  if repo_root="$(git rev-parse --show-toplevel)"; then
    :
  else
    rc="$?"
    warn_exit "${rc}" "git_rev_parse"
    return "$?"
  fi

  if cd "${repo_root}"; then
    :
  else
    rc="$?"
    warn_exit "${rc}" "cd_repo_root"
    return "$?"
  fi

  log_dir="${HOME}/Library/Logs/hongstr"
  if mkdir -p "${log_dir}"; then
    :
  else
    rc="$?"
    warn_exit "${rc}" "mkdir_log_dir"
    return "$?"
  fi

  if acquire_lock; then
    :
  else
    rc="$?"
    if [[ "${rc}" == "2" ]]; then
      return 0
    fi
    warn_exit "${rc}" "lock_acquire"
    return "$?"
  fi

  python_bin="${repo_root}/.venv/bin/python"
  sync_script="${repo_root}/scripts/obsidian_sync.py"
  index_script="${repo_root}/scripts/obsidian_lancedb_index.py"

  if [[ ! -x "${python_bin}" ]]; then
    warn_exit 127 "python_missing"
    return "$?"
  fi

  if "${python_bin}" "${sync_script}"; then
    :
  else
    rc="$?"
    warn_exit "${rc}" "obsidian_sync"
    return "$?"
  fi

  detect_provider

  if "${python_bin}" "${index_script}" --incremental "${PROVIDER_ARGS[@]}"; then
    :
  else
    rc="$?"
    warn_exit "${rc}" "obsidian_lancedb_index"
    return "$?"
  fi

  echo "OK ${JOB_LABEL}: start_utc=${start_utc} end_utc=$(now_utc) provider=${PROVIDER}"
  return 0
}

main() {
  if run_job; then
    return 0
  else
    return "$?"
  fi
}

main "$@"
