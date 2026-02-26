#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/check_allowlist_changes.sh [options]

Options:
  --worktree            Check local worktree changes (default)
  --staged              Check staged changes only
  --against-ref <ref>   Check git diff <ref>...HEAD
  --list-changed        Print changed files
  -h, --help            Show this help

Allowlist roots:
  - docs/**
  - _local/**
  - research/**
  - scripts/** (non-prod semantics only)
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

is_allowed_path() {
  local p="$1"
  case "$p" in
    docs/*|_local/*|research/*)
      return 0
      ;;
    scripts/*)
      # Keep scripts changes limited to non-prod semantics.
      case "$p" in
        scripts/auto_pr.sh|scripts/check_allowlist_changes.sh)
          return 0
          ;;
        scripts/*)
          # Block typical prod/runtime execution scripts.
          case "$p" in
            scripts/run_*|scripts/daily_*|scripts/execute_*|scripts/recover_*|scripts/backfill_*|scripts/ingest_*|scripts/aggregate_*|scripts/notify_*|scripts/one_click_dashboard.sh|scripts/run_dashboard.sh)
              return 1
              ;;
            *)
              return 0
              ;;
          esac
          ;;
      esac
      ;;
    *)
      return 1
      ;;
  esac
}

CHANGED="$(collect_changes)"

if [[ "$LIST_CHANGED" -eq 1 ]]; then
  if [[ -n "$CHANGED" ]]; then
    printf "%s\n" "$CHANGED"
  fi
fi

if [[ -z "$CHANGED" ]]; then
  exit 0
fi

BAD=0
while IFS= read -r path; do
  [[ -z "$path" ]] && continue

  # Data artifacts are always forbidden.
  case "$path" in
    data/*)
      echo "DISALLOWED (data artifact): $path" >&2
      BAD=1
      continue
      ;;
  esac

  if ! is_allowed_path "$path"; then
    echo "DISALLOWED (outside allowlist): $path" >&2
    BAD=1
  fi
done <<< "$CHANGED"

if [[ "$BAD" -ne 0 ]]; then
  echo "Allowlist check failed." >&2
  exit 1
fi
