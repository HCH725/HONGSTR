#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==========================================="
echo "  HONGSTR Phase 4 ML End-to-End Demo       "
echo "==========================================="

echo "1) Checking / Building Features (1h)"
bash scripts/build_features.sh --freq 1h --symbols "BTCUSDT ETHUSDT BNBUSDT" --start 2020-01-01 --end now

echo "2) Building Labels (1h, Horizon 24)"
bash scripts/build_labels.sh --freq 1h --horizon 24

echo "3) Running Baseline ML Evaluator"
bash scripts/run_ml_baseline.sh --freq 1h --horizon 24

echo "==========================================="
echo "  Phase 4 ML Workflow Complete             "
echo "  Find your results at:                    "
echo "  reports/research/ml/phase4_results.md    "
echo "==========================================="

exit 0
