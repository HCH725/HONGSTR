#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${REPO_ROOT}/docs/skills"
LOCAL_CACHE="${REPO_ROOT}/_local/skills_cache"
HOME_CACHE="${HOME}/.hongstr/skills"

DRY_RUN=0
FORCE=0
DEST=""

usage() {
  cat <<'USAGE'
Usage: bash scripts/install_hongstr_skills.sh [--dry-run] [--dest <path>] [--force]

Copy docs skill packs from docs/skills/ to a local cache directory.

Options:
  --dry-run       Show what would be copied; do not write files.
  --dest <path>   Destination directory. Default is:
                  1) _local/skills_cache (if gitignored), else
                  2) ~/.hongstr/skills
  --force         Allow copying into a non-empty destination.
  -h, --help      Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --dest)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --dest requires a path" >&2
        usage
        exit 2
      fi
      DEST="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -d "$SRC_DIR" ]]; then
  echo "ERROR: source skill directory not found: $SRC_DIR" >&2
  exit 1
fi

if [[ -z "$DEST" ]]; then
  if command -v git >/dev/null 2>&1 && git -C "$REPO_ROOT" check-ignore -q "_local/skills_cache/"; then
    DEST="$LOCAL_CACHE"
    DEFAULT_NOTE="default(_local/skills_cache gitignored)"
  else
    DEST="$HOME_CACHE"
    DEFAULT_NOTE="default(~/.hongstr/skills fallback)"
  fi
else
  DEFAULT_NOTE="user-specified"
fi

# Expand leading ~ for user-provided --dest.
if [[ "$DEST" == "~" ]]; then
  DEST="$HOME"
elif [[ "$DEST" == ~/* ]]; then
  DEST="$HOME/${DEST#~/}"
fi

echo "Source:      $SRC_DIR"
echo "Destination: $DEST"
echo "Mode:        $DEFAULT_NOTE"
echo "Dry-run:     $DRY_RUN"
echo "Force:       $FORCE"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo
  echo "Files to copy:"
  find "$SRC_DIR" -type f | sed "s#^${REPO_ROOT}/##" | sort
  exit 0
fi

if [[ -d "$DEST" ]] && [[ "$FORCE" -ne 1 ]]; then
  if [[ -n "$(find "$DEST" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ]]; then
    echo "ERROR: destination is not empty: $DEST" >&2
    echo "Re-run with --force to allow overwrite." >&2
    exit 1
  fi
fi

mkdir -p "$DEST"

if command -v rsync >/dev/null 2>&1; then
  rsync -a "$SRC_DIR"/ "$DEST"/
else
  cp -R "$SRC_DIR"/. "$DEST"/
fi

echo "Install complete: copied skills docs to $DEST"
