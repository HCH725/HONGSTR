#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/check_allowlist_changes.sh [options]

Options:
  --worktree             Check unstaged + staged + untracked changes (default)
  --staged               Check staged changes only
  --against-ref <ref>    Check git diff <ref>...HEAD
  --list-changed         Print changed files
  -h, --help             Show help

Allowlist (Phase B Auto-PR):
  - docs/**
  - research/**
  - _local/**
  - scripts/auto_pr.sh
  - scripts/check_allowlist_changes.sh

Hard blocks:
  - src/hongstr/**
  - data/**
EOF
}

MODE="worktree"
AGAINST_REF=""
LIST_CHANGED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worktree)
      MODE="worktree"
      shift
      ;;
    --staged)
      MODE="staged"
      shift
      ;;
    --against-ref)
      AGAINST_REF="${2:-}"
      if [[ -z "$AGAINST_REF" ]]; then
        echo "ERROR: --against-ref requires a value" >&2
        exit 2
      fi
      MODE="against_ref"
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
      echo "ERROR: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

collect_changes() {
  case "$MODE" in
    staged)
      git diff --cached --name-only --diff-filter=ACMRD
      ;;
    against_ref)
      git diff --name-only "${AGAINST_REF}...HEAD"
      ;;
    *)
      {
        git diff --name-only
        git diff --cached --name-only
        git ls-files --others --exclude-standard
      }
      ;;
  esac | awk 'NF' | sort -u
}

is_allowed() {
  local p="$1"
  case "$p" in
    docs/*|research/*|_local/*|scripts/auto_pr.sh|scripts/check_allowlist_changes.sh)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

CHANGED="$(collect_changes)"

if [[ "$LIST_CHANGED" -eq 1 ]] && [[ -n "$CHANGED" ]]; then
  printf "%s\n" "$CHANGED"
fi

if [[ -z "$CHANGED" ]]; then
  exit 0
fi

BAD=0
while IFS= read -r p; do
  [[ -z "$p" ]] && continue
  case "$p" in
    src/hongstr/*)
      echo "DISALLOWED (core protected): $p" >&2
      BAD=1
      continue
      ;;
    data/*)
      echo "DISALLOWED (data artifact): $p" >&2
      BAD=1
      continue
      ;;
  esac
  if ! is_allowed "$p"; then
    echo "DISALLOWED (outside allowlist): $p" >&2
    BAD=1
  fi
done <<< "$CHANGED"

if [[ "$BAD" -ne 0 ]]; then
  echo "Allowlist check failed." >&2
  exit 1
fi
