#!/bin/bash
# scripts/retention_cleanup.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DRY_RUN=false
if [[ "${1:-}" == "--dry_run" ]]; then
    DRY_RUN=true
    echo "--- DRY RUN MODE ---"
fi

DATA_DIR="$REPO_ROOT/data"
REALTIME_DIR="$DATA_DIR/realtime"
BACKTESTS_DIR="$DATA_DIR/backtests"

echo "--- Retention Cleanup ($(date)) ---"

# 1. Realtime Data
# 保留 jsonl 14 天；>14 天 gzip；>45 天刪除
if [ -d "$REALTIME_DIR" ]; then
    echo "Cleaning $REALTIME_DIR..."
    
    # Gzip > 14 days
    find "$REALTIME_DIR" -maxdepth 2 -name "*.jsonl" -type f -mtime +14 | while read -r line; do
        if $DRY_RUN; then echo "[DRY] gzip $line"; else gzip "$line"; fi
    done
    
    # Delete > 45 days (both .jsonl and .gz)
    find "$REALTIME_DIR" -maxdepth 2 \( -name "*.jsonl" -o -name "*.gz" \) -type f -mtime +45 | while read -r line; do
        if $DRY_RUN; then echo "[DRY] rm $line"; else rm "$line"; fi
    done
fi

# 2. Backtests
# 保留 90 天；另外若 runs > 200，刪除最舊直到剩 200
if [ -d "$BACKTESTS_DIR" ]; then
    echo "Cleaning $BACKTESTS_DIR..."
    
    # Delete > 90 days
    find "$BACKTESTS_DIR" -maxdepth 2 -type d -mtime +90 | while read -r line; do
        if [[ "$line" == "$BACKTESTS_DIR" ]]; then continue; fi # Safety
        if $DRY_RUN; then echo "[DRY] rm -rf $line"; else rm -rf "$line"; fi
    done
    
    # Keep latest 200
    # Group by all runs under subfolders (YYYY-MM-DD/run_id)
    # Actually finding directories that contain summary.json or similar
    all_runs=$(find "$BACKTESTS_DIR" -mindepth 2 -maxdepth 2 -type d | xargs ls -td 2>/dev/null)
    count=$(echo "$all_runs" | wc -l)
    
    if [ "$count" -gt 200 ]; then
        to_del=$((count - 200))
        echo "Too many runs ($count), deleting oldest $to_del..."
        echo "$all_runs" | tail -n "$to_del" | while read -r line; do
            if $DRY_RUN; then echo "[DRY] rm -rf $line"; else rm -rf "$line"; fi
        done
    fi
fi

echo "--- Cleanup Complete ---"
