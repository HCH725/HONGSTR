#!/bin/bash
# HONGSTR Autonomous Research Loop v2 Runner
# Usage: bash scripts/run_research_loop.sh [--once] [--dry-run]
# Stability-first: always exits 0. Loads .env. Prevents re-entry via lock file.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Load env ──────────────────────────────────────────────────────────────────
if [[ -f "${REPO_ROOT}/scripts/load_env.sh" ]]; then
  source "${REPO_ROOT}/scripts/load_env.sh"
elif [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${REPO_ROOT}/.env"
  set +a
fi

export PYTHONPATH="${REPO_ROOT}"

# ── Parse flags ───────────────────────────────────────────────────────────────
DRY_RUN_FLAG=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN_FLAG="--dry-run" ;;
    --once)    ;; # default behavior, single execution
    *) echo "Unknown flag: $arg" >&2 ;;
  esac
done

echo "[research_loop] Starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Execute (stability wrapper: always exit 0) ────────────────────────────────
"${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/research/loop/research_loop.py" ${DRY_RUN_FLAG} || true

echo "[research_loop] Finished at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
exit 0
