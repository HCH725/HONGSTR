#!/usr/bin/env bash
# refresh_state.sh - One-Click Read-Only State Refresh & Dashboard Snapshots
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=========================================="
echo "    Read-Only State & Dashboard Refresh   "
echo "=========================================="

# Enforce canonical state writer boundary before refresh flow.
.venv/bin/python scripts/check_state_writer_boundary.py --strict

# Helpers to prevent hard crashes
run_step() {
    local title="$1"
    shift
    echo -e "\n---> [START] $title"
    set +e
    "$@"
    local rc=$?
    set -e
    if [ $rc -ne 0 ]; then
        echo -e "---> [WARN] Step failed with Exit Code $rc. (Continuing to support partial builds...)"
    else
        echo -e "---> [DONE] $title"
    fi
}

run_step "1. Update Coverage Atomic Table" \
    .venv/bin/python scripts/coverage_update.py --scan-root data/backtests --limit 1000 --template trend_mvp_v1 || true

run_step "2. Apply Coverage Semantics Gate (Atomic)" \
    .venv/bin/python scripts/semantics_check.py || true

run_step "3. Generate Regime Monitor Atomic Snapshot" \
    .venv/bin/python scripts/phase4_regime_monitor.py || true

run_step "4. Generate Brake Health Atomic Snapshot" \
    .venv/bin/python scripts/brake_healthcheck.py || true

# Note: scripts/coverage_validate.py might not exist yet, we ensure it's gracefully ignored if it doesn't
if [ -f "scripts/coverage_validate.py" ]; then
    run_step "5. Validate Coverage Table" \
        .venv/bin/python scripts/coverage_validate.py || true
else
    echo -e "\n---> [SKIP] scripts/coverage_validate.py (Not implemented, skipping smoothly)"
fi

if [ -f "scripts/strategy_pool_update.py" ]; then
    run_step "6. Update Strategy Pool" \
        .venv/bin/python scripts/strategy_pool_update.py || true
else
    echo -e "\n---> [SKIP] scripts/strategy_pool_update.py (Not implemented, skipping smoothly)"
fi

run_step "7. Generate Dashboard Snapshots (Canonical data/state Writer)" \
    .venv/bin/python scripts/state_snapshots.py

echo -e "\n=========================================="
echo "               TL;DR REPORT               "
echo "=========================================="

echo "Timestamp (UTC): $(date -u)"

if [ -f data/state/coverage_summary.json ]; then
    COV_COUNT=$(cat data/state/coverage_summary.json | grep -o '"count": [0-9]*' | cut -d ' ' -f 2)
    echo "Coverage Table Rows  : $COV_COUNT"
else
    echo "Coverage Table Rows  : N/A (Missing snapshot)"
fi

if [ -f data/state/strategy_pool_summary.json ]; then
    echo "Strategy Pool Leaders: "
    # Basic bash parsing to show Top 5 if available
    python3 -c '
import json, math, sys
def fmt_metric(v):
    if v is None:
        return "UNKNOWN"
    try:
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return "UNKNOWN"
        return f"{fv:.2f}"
    except Exception:
        return "UNKNOWN"
try:
    with open("data/state/strategy_pool_summary.json") as f:
        data = json.load(f)
        leaders = data.get("leaderboard", [])
        if not leaders:
            print("  No candidates available.")
        else:
            for idx, c in enumerate(leaders[:5]):
                cid = c.get("id")
                cscore = fmt_metric(c.get("score"))
                csharpe = fmt_metric(c.get("sharpe"))
                creturn = fmt_metric(c.get("return"))
                status = str(c.get("metrics_status", "UNKNOWN"))
                reason = c.get("metrics_unavailable_reason")
                suffix = f" | Metrics {status}"
                if reason:
                    suffix += f" ({reason})"
                print(f"  {idx+1}. {cid}: Score {cscore} | Sharpe {csharpe} | Return {creturn}{suffix}")
except Exception as e:
    print(f"  Error reading pool summary: {e}")
'
else
    echo "Strategy Pool Leaders: N/A (Missing snapshot)"
fi

echo "=========================================="
exit 0
