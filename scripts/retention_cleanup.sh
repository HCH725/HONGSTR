#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load .env if present (TG only; do not fail if missing)
if [ -f "scripts/load_env.sh" ]; then
  # shellcheck disable=SC1091
  source scripts/load_env.sh || true
fi

# Config (override via env)
RETENTION_DAYS="${RETENTION_DAYS:-30}"
MAX_RUNS="${MAX_RUNS:-1200}"
DRY_RUN="${DRY_RUN:-0}"
DATA_DIR="${DATA_DIR:-data/backtests}"

notify() {
  local title="$1"; shift
  local status="$1"; shift
  local body="$1"; shift || true
  if [ -x "scripts/notify_telegram.sh" ]; then
    bash scripts/notify_telegram.sh --title "$title" --status "$status" --body "$body" || true
  fi
}

echo "=== Retention Cleanup Started ($(date)) ==="
echo "REPO_ROOT=$REPO_ROOT"
echo "DATA_DIR=$DATA_DIR"
echo "RETENTION_DAYS=$RETENTION_DAYS"
echo "MAX_RUNS=$MAX_RUNS"
echo "DRY_RUN=$DRY_RUN"

if [ ! -d "$DATA_DIR" ]; then
  echo "WARN: $DATA_DIR not found; nothing to do"
  exit 0
fi

tmp_runs="$(mktemp)"
tmp_old="$(mktemp)"
tmp_remaining="$(mktemp)"
tmp_delete="$(mktemp)"
trap 'rm -f "$tmp_runs" "$tmp_old" "$tmp_remaining" "$tmp_delete"' EXIT

find "$DATA_DIR" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | sort > "$tmp_runs"
TOTAL="$(wc -l < "$tmp_runs" | tr -d ' ')"
echo "TOTAL_RUNS=$TOTAL"
if [ "$TOTAL" = "0" ]; then
  echo "No runs."
  exit 0
fi

CUTOFF_DATE="$(python3 - <<PY
import datetime, os
days=int(os.environ.get("RETENTION_DAYS","30"))
cut=(datetime.datetime.utcnow().date() - datetime.timedelta(days=days))
print(cut.isoformat())
PY
)"
echo "CUTOFF_DATE_UTC=$CUTOFF_DATE"

is_yyyy_mm_dd() {
  case "$1" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) return 0 ;;
    *) return 1 ;;
  esac
}

OLD_BY_DAYS=0
KEEP_BY_DAYS_OR_UNKNOWN=0

while IFS= read -r d; do
  [ -z "$d" ] && continue
  parent="$(basename "$(dirname "$d")")"
  if is_yyyy_mm_dd "$parent"; then
    if [ "$parent" '<' "$CUTOFF_DATE" ]; then
      echo "$d" >> "$tmp_old"
      OLD_BY_DAYS=$((OLD_BY_DAYS + 1))
    else
      echo "$d" >> "$tmp_remaining"
      KEEP_BY_DAYS_OR_UNKNOWN=$((KEEP_BY_DAYS_OR_UNKNOWN + 1))
    fi
  else
    echo "$d" >> "$tmp_remaining"
    KEEP_BY_DAYS_OR_UNKNOWN=$((KEEP_BY_DAYS_OR_UNKNOWN + 1))
  fi
done < "$tmp_runs"

echo "OLD_BY_DAYS=$OLD_BY_DAYS"
echo "KEEP_BY_DAYS_OR_UNKNOWN=$KEEP_BY_DAYS_OR_UNKNOWN"

# Start delete list with old-by-days candidates
cat "$tmp_old" > "$tmp_delete"

REMAIN_COUNT="$KEEP_BY_DAYS_OR_UNKNOWN"
if [ "$REMAIN_COUNT" -gt "$MAX_RUNS" ]; then
  EXTRA=$((REMAIN_COUNT - MAX_RUNS))
  echo "CAP_TRIGGER: remaining=$REMAIN_COUNT > MAX_RUNS=$MAX_RUNS, will delete EXTRA=$EXTRA oldest-by-mtime"
  python3 - "$tmp_remaining" <<'PY' | head -n "$EXTRA" >> "$tmp_delete"
import os,sys
p=sys.argv[1]
with open(p,'r',encoding='utf-8',errors='ignore') as f:
    paths=[line.strip() for line in f if line.strip()]
paths.sort(key=lambda x: os.path.getmtime(x))
for x in paths:
    print(x)
PY
fi

# Dedup while preserving order
awk 'NF && !seen[$0]++' "$tmp_delete" > "$tmp_delete.dedup"
mv "$tmp_delete.dedup" "$tmp_delete"

DELN="$(wc -l < "$tmp_delete" | tr -d ' ')"
echo "DELETE_PLANNED=$DELN"
if [ "$DELN" = "0" ]; then
  echo "Nothing to delete."
  notify "HONGSTR retention" "INFO" "No deletions needed. total=$TOTAL cutoff=$CUTOFF_DATE max_runs=$MAX_RUNS"
  exit 0
fi

PREVIEW="$(head -n 20 "$tmp_delete")"
BODY="Will delete $DELN runs (cutoff<$CUTOFF_DATE and cap>$MAX_RUNS). DRY_RUN=$DRY_RUN
Preview (first 20):
$PREVIEW"
notify "HONGSTR retention" "WARN" "$BODY"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN=1 -> not deleting."
  exit 0
fi

while IFS= read -r d; do
  [ -z "$d" ] && continue
  rm -rf "$d"
done < "$tmp_delete"

AFTER="$(find "$DATA_DIR" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | wc -l | tr -d ' ')"
echo "TOTAL_AFTER=$AFTER"

notify "HONGSTR retention" "INFO" "Deleted $DELN runs. total_before=$TOTAL total_after=$AFTER cutoff=$CUTOFF_DATE max_runs=$MAX_RUNS"
echo "=== Retention Cleanup Complete ($(date)) ==="
