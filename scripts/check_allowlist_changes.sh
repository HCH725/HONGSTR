#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RANGE="${1:-origin/main...HEAD}"
PY_BIN="${PY_BIN:-./.venv/bin/python}"
if [ ! -x "$PY_BIN" ]; then
  PY_BIN="python3"
fi

mapfile -t CHANGED < <(git diff --name-only "$RANGE")

if [ "${#CHANGED[@]}" -eq 0 ]; then
  echo '{"ok":true,"paths":[],"bad_paths":[]}'
  exit 0
fi

printf '%s\n' "${CHANGED[@]}" | "$PY_BIN" scripts/auto_pr_utils.py check
