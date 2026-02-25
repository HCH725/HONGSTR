#!/usr/bin/env bash
# scripts/find_full_runs.sh - Scan for backtest runs with selection/summary/gate/regime artifacts.
# Output: <date>/<id> | mtime | flags (S:selection, U:summary, G:gate, R:regime, O:optimizer)

set -euo pipefail

BACKTEST_DIR="data/backtests"
TOP_N=10
REQUIRE_SELECTION=true
GREP_PATTERN=""

show_help() {
    echo "Usage: $0 [--top N] [--require-selection true|false] [--grep PATTERN]"
    echo "  --top N                   Number of runs to show (default: 10)"
    echo "  --require-selection bool  Only show runs with selection.json (default: true)"
    echo "  --grep PATTERN            Self-check: Exit 0 if PATTERN found in results"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --top) TOP_N="$2"; shift 2 ;;
        --require-selection) REQUIRE_SELECTION="$2"; shift 2 ;;
        --grep) GREP_PATTERN="$2"; shift 2 ;;
        -h|--help) show_help ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ ! -d "$BACKTEST_DIR" ]]; then
    echo "Error: Directory $BACKTEST_DIR not found."
    exit 1
fi

echo "Scanning $BACKTEST_DIR (All dates, 3 levels deep)..."
echo "--------------------------------------------------------------------------------"
echo "RUN PATH | MTIME | FLAGS (S=Select, U=Summ, G=Gate, R=Regi, O=Opti)"
echo "--------------------------------------------------------------------------------"

# Find summary.json files across all date subdirs
# We use mindepth 3 to skip the date dir itself
results_found=0
matched_grep=false

# We use stat -f "%m %N" for macOS compatibility
# Instead of head -n N inside the loop, we filter first then head
temp_file=$(mktemp)
find "$BACKTEST_DIR" -mindepth 3 -maxdepth 3 -name "summary.json" -exec stat -f "%m %N" {} + | sort -rn > "$temp_file"

while read -r line; do
    [[ -z "$line" ]] && continue
    mtime_epoch=$(echo "$line" | cut -d' ' -f1)
    summary_path=$(echo "$line" | cut -d' ' -f2)
    run_dir=$(dirname "$summary_path")
    
    # Relative path from backtests
    rel_path=${run_dir#$BACKTEST_DIR/}
    
    # Flags
    has_selection=false
    [[ -f "$run_dir/selection.json" ]] && has_selection=true
    
    if [[ "$REQUIRE_SELECTION" == "true" && "$has_selection" == "false" ]]; then
        continue
    fi

    flags=""
    [[ "$has_selection" == "true" ]] && flags+="S" || flags+="."
    [[ -f "$run_dir/summary.json" ]] && flags+="U" || flags+="."
    [[ -f "$run_dir/gate.json" ]] && flags+="G" || flags+="."
    [[ -f "$run_dir/regime_report.json" ]] && flags+="R" || flags+="."
    
    if [[ -f "$run_dir/optimizer_regime.json" || -f "$run_dir/optimizer.json" ]]; then
        flags+="O"
    else
        flags+="."
    fi
    
    mtime_human=$(date -u -r "${mtime_epoch%.*}" +"%Y-%m-%d %H:%M")
    
    is_full="[PARTIAL]"
    if [[ "${flags:0:1}" == "S" && "${flags:1:1}" == "U" ]]; then
        is_full="[  FULL ]"
    fi
    
    row_text=$(printf "%-40s | %s | %-5s %s" "$rel_path" "$mtime_human" "$flags" "$is_full")
    echo "$row_text"
    
    if [[ -n "$GREP_PATTERN" && "$rel_path" == *"$GREP_PATTERN"* ]]; then
        matched_grep=true
    fi

    results_found=$((results_found + 1))
    if [[ $results_found -ge $TOP_N ]]; then
        break
    fi
done < "$temp_file"

rm -f "$temp_file"

echo "--------------------------------------------------------------------------------"
echo "Total $results_found displayed."

if [[ -n "$GREP_PATTERN" ]]; then
    if [[ "$matched_grep" == "true" ]]; then
        echo "Check OK: Found pattern '$GREP_PATTERN'"
        exit 0
    else
        echo "Check FAILED: Pattern '$GREP_PATTERN' not found in top $TOP_N results"
        exit 1
    fi
fi
