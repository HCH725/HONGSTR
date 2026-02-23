#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FREQ="1h"
HORIZON="24"
SYMBOLS="BTCUSDT ETHUSDT BNBUSDT"
START_DATE="2020-01-01"

echo "=========================================="
echo "    HONGSTR Daily ML Maintenance Tool     "
echo "=========================================="

# Helpers to prevent hard crashes for stability-first rule
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

run_step "Data Coverage Sanity Check" \
    bash scripts/check_data_coverage.sh

run_step "1. Build Features (Freq: $FREQ, Period: $START_DATE - Now)" \
    bash scripts/build_features.sh --freq "$FREQ" --symbols "$SYMBOLS" --start "$START_DATE" --end now

run_step "2. Build Labels (Freq: $FREQ, Horizon: $HORIZON)" \
    bash scripts/build_labels.sh --freq "$FREQ" --horizon "$HORIZON"

run_step "3. Train ML Baseline Models" \
    bash scripts/run_ml_baseline.sh --freq "$FREQ" --horizon "$HORIZON"

run_step "4. Seal & Pack Model Artifacts" \
    bash scripts/build_model_artifact.sh --freq "$FREQ" --horizon "$HORIZON"

run_step "5. Extrapolate Signal Inferences (Read-Only Score Matrix)" \
    bash scripts/build_signals.sh --freq "$FREQ" --horizon "$HORIZON"

run_step "6. Compile Non-Technical Partner Summary (Evidence)" \
    .venv/bin/python scripts/report_ml_evidence.py --freq "$FREQ" --horizon "$HORIZON" --latest-backtest auto

echo -e "\n=========================================="
echo "  All automated operational tasks finished! "
echo "  Review reports/research/ml/evidence_summary.md for the TL;DR. "
echo "=========================================="
exit 0
