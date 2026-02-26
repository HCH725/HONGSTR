#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/check_allowlist_changes.sh [--against-ref <ref>] [--list-changed]

Modes:
  - default: validate changed files in current worktree (staged + unstaged + untracked)
  - --against-ref <ref>: validate files in `git diff --name-only <ref>...HEAD`

Policy:
  Allowed paths:
    - docs/**
    - ops/**/*.md
  Forbidden:
    - data/**
    - everything else
  Note:
    - untracked data/** files are ignored (to allow local generator outputs)

Exit codes:
  0: all changed files are allowlisted
  1: found non-allowlisted paths
  2: invalid usage
EOF
}

AGAINST_REF=""
LIST_CHANGED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --against-ref)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --against-ref requires a value" >&2
        usage
        exit 2
      fi
      AGAINST_REF="$2"
      shift 2
      ;;
    --list-changed)
      LIST_CHANGED=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

collect_worktree_changes() {
  local line=""
  local code=""
  local path=""
  git status --porcelain | while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    code="${line:0:2}"
    path="${line:3}"
    [[ -z "$path" ]] && continue
    # Optional generators may produce untracked data artifacts; ignore them.
    if [[ "$code" == "??" && "$path" == data/* ]]; then
      continue
    fi
    echo "$path"
  done | awk 'NF' | sort -u
}

collect_ref_changes() {
  git diff --name-only "${AGAINST_REF}...HEAD" | awk 'NF' | sort -u
}

is_allowlisted() {
  local path="$1"
  [[ "$path" == docs/* ]] && return 0
  [[ "$path" =~ ^ops/.+\.md$ ]] && return 0
  return 1
}

changed_files=()
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  changed_files+=("$line")
done < <(
  if [[ -n "$AGAINST_REF" ]]; then
    collect_ref_changes
  else
    collect_worktree_changes
  fi
)

if [[ "$LIST_CHANGED" -eq 1 ]]; then
  for p in "${changed_files[@]}"; do
    echo "$p"
  done
fi

if [[ ${#changed_files[@]} -eq 0 ]]; then
  exit 0
fi

unexpected=()
for path in "${changed_files[@]}"; do
  if [[ "$path" == data/* ]]; then
    unexpected+=("$path")
    continue
  fi
  if ! is_allowlisted "$path"; then
    unexpected+=("$path")
  fi
done

if [[ ${#unexpected[@]} -gt 0 ]]; then
  echo "ERROR: found non-allowlisted changes:" >&2
  for p in "${unexpected[@]}"; do
    echo "  - $p" >&2
  done
  echo "Allowed: docs/** and ops/**/*.md only." >&2
  exit 1
fi

exit 0
