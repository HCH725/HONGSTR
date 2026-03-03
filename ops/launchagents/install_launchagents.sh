#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_DIR="${REPO_ROOT}/ops/launchagents"
DEST_DIR="${HOME}/Library/LaunchAgents"
RESTART=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage:
  bash ops/launchagents/install_launchagents.sh [--dry-run] [--restart]

Options:
  --dry-run   Show planned file sync and launchctl actions without writing.
  --restart   After sync, bootout/bootstrap each synced com.hongstr.* plist.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --restart) RESTART=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 2 ;;
  esac
  shift
done

mkdir -p "$DEST_DIR"

plist_files=()
while IFS= read -r f; do
  plist_files+=("$f")
done < <(find "$SRC_DIR" -maxdepth 1 -type f -name 'com.hongstr.*.plist' | sort)

if [[ ${#plist_files[@]} -eq 0 ]]; then
  echo "No com.hongstr.*.plist found under $SRC_DIR"
  exit 1
fi

echo "Sync source: $SRC_DIR"
echo "Sync dest  : $DEST_DIR"
echo "Repo root  : $REPO_ROOT"
echo

for src in "${plist_files[@]}"; do
  base="$(basename "$src")"
  dst="${DEST_DIR}/${base}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] render+copy $src -> $dst"
  else
    sed "s|__REPO_ROOT__|${REPO_ROOT}|g" "$src" > "$dst"
    plutil -lint "$dst" >/dev/null
    echo "synced: $base"
  fi
done

if [[ "$RESTART" -eq 1 ]]; then
  echo
  echo "Restarting synced jobs (bootout -> sleep -> bootstrap)"
  for src in "${plist_files[@]}"; do
    base="$(basename "$src")"
    label="${base%.plist}"
    dst="${DEST_DIR}/${base}"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] launchctl bootout gui/$(id -u) $dst"
      echo "[dry-run] launchctl bootstrap gui/$(id -u) $dst"
      continue
    fi
    launchctl bootout "gui/$(id -u)" "$dst" 2>/dev/null || true
    sleep 2
    launchctl bootstrap "gui/$(id -u)" "$dst"
    launchctl print "gui/$(id -u)/${label}" | rg 'state =|pid =|last exit|active count' || true
  done
fi

echo
echo "Done."
