#!/bin/bash
# Find the directory of the latest completed backtest (containing summary.json)
# Usage: ./scripts/get_latest_completed_dir.sh

# Find all summary.json files, sort by time (newest first), take top 1
# reliable on macOS/BSD and Linux if files are not too many (~50 retention)
LATEST_SUMMARY=$(find data/backtests -name summary.json -type f -print0 2>/dev/null | xargs -0 ls -t 2>/dev/null | head -n 1)

if [ -z "$LATEST_SUMMARY" ]; then
    echo "No completed backtest found (summary.json missing)" >&2
    exit 1
fi

dirname "$LATEST_SUMMARY"
