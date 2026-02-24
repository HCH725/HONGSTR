#!/usr/bin/env bash
# scripts/find_full_runs.sh - Scan for backtest runs with selection/summary/gate/regime artifacts.
# Output: <date>/<id> | mtime | flags (S:selection, U:summary, G:gate, R:regime, O:optimizer)

set -euo pipefail

BACKTEST_DIR="data/backtests"
TOP_N=10

show_help() {
    echo "Usage: $0 [--top N]"
    echo "  --top N    Number of latest runs to show (default: 10)"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --top) TOP_N="$2"; shift 2 ;;
        -h|--help) show_help ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ ! -d "$BACKTEST_DIR" ]]; then
    echo "Error: Directory $BACKTEST_DIR not found."
    exit 1
fi

echo "Scanning $BACKTEST_DIR (2 layers)..."
echo "--------------------------------------------------------------------------------"
echo "RUN PATH | MTIME | FLAGS (S=Select, U=Summ, G=Gate, R=Regi, O=Opti)"
echo "--------------------------------------------------------------------------------"

# Find summary.json files up to 3 levels deep (date/run_id/summary.json)
# We use stat -f "%m %N" for macOS compatibility
find "$BACKTEST_DIR" -maxdepth 3 -name "summary.json" -exec stat -f "%m %N" {} + | sort -rn | head -n "$TOP_N" | while read -r line; do
    mtime_epoch=$(echo "$line" | cut -d' ' -f1)
    summary_path=$(echo "$line" | cut -d' ' -f2)
    run_dir=$(dirname "$summary_path")
    
    # Relative path from backtests
    rel_path=${run_dir#$BACKTEST_DIR/}
    
    # Flags
    flags=""
    [[ -f "$run_dir/selection.json" ]] && flags+="S" || flags+="."
    [[ -f "$run_dir/summary.json" ]] && flags+="U" || flags+="."
    [[ -f "$run_dir/gate.json" ]] && flags+="G" || flags+="."
    [[ -f "$run_dir/regime_report.json" ]] && flags+="R" || flags+="."
    
    # Optimizer can be either optimizer.json or optimizer_regime.json
    if [[ -f "$run_dir/optimizer_regime.json" || -f "$run_dir/optimizer.json" ]]; then
        flags+="O"
    else
        flags+="."
    fi
    
    # Using 'date' for macOS/BSD compatibility
    mtime_human=$(date -u -r "${mtime_epoch%.*}" +"%Y-%m-%d %H:%M")
    
    is_full="[PARTIAL]"
    if [[ "${flags:0:1}" == "S" && "${flags:1:1}" == "U" ]]; then
        is_full="[  FULL ]"
    fi
    
    printf "%-40s | %s | %-5s %s\n" "$rel_path" "$mtime_human" "$flags" "$is_full"
done

echo "--------------------------------------------------------------------------------"
echo "Total top $TOP_N displayed."
