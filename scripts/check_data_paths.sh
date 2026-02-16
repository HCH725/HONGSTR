#!/bin/bash
# scripts/check_data_paths.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Pick Python
PY="${PY:-./.venv/bin/python}"
if [ ! -x "$PY" ]; then
    PY="python3"
fi

SYMBOLS="BTCUSDT ETHUSDT BNBUSDT"
DERIVED_ROOT="data/derived"

echo "=== HONGSTR Data Path Check ==="

missing_any=false

for sym in $SYMBOLS; do
    echo "Checking $sym..."
    
    # Check 1m source
    FILE_1M="$DERIVED_ROOT/$sym/1m/klines.jsonl"
    if [ -f "$FILE_1M" ]; then
        count=$(wc -l < "$FILE_1M")
        echo "  [OK] 1m source: $count lines"
    else
        echo "  [MISSING] 1m source: $FILE_1M"
        missing_any=true
    fi
    
    # Check TFs
    for tf in 5m 15m 1h 4h; do
        FILE_TF="$DERIVED_ROOT/$sym/$tf/klines.jsonl"
        if [ -f "$FILE_TF" ]; then
             echo "  [OK] $tf: exists"
        else
             echo "  [MISSING] $tf: $FILE_TF"
             missing_any=true
        fi
    done
done

if $missing_any; then
    echo -e "\nRecommendations:"
    echo "1. To ingest missing 1m data: $PY scripts/ingest_historical.py --symbol SYMBOL"
    echo "2. To aggregate missing TFs: $PY scripts/aggregate_data.py --symbol SYMBOL"
    echo "Or run the daily ETL to sync all: bash scripts/daily_etl.sh"
else
    echo -e "\nAll derived data paths look good."
fi
