#!/usr/bin/env bash
# verify_phase6.sh - Executes constraint smoke tests for Phase 6 validation
set -e

echo "=========================================="
echo "    Phase 6 Read-Only Smoke Validation    "
echo "=========================================="

echo "[1] Checking core engine isolation (diff src/hongstr)..."
CORE_DIFF=$(git diff HEAD~1..HEAD -- src/hongstr | wc -l | tr -d ' ')
if [ "$CORE_DIFF" -ne 0 ]; then
    echo "FAIL: Core engine modified ($CORE_DIFF lines)."
    exit 1
fi
echo "PASS: Core diff = 0"

echo "[2] Checking for un-tracked parquet artifacts..."
set +e
PARQUET_FOUND=$(git ls-files | rg '\.(parquet|pkl)$')
set -e
if [ -n "$PARQUET_FOUND" ]; then
    echo "FAIL: Large data artifacts tracked in git repository."
    echo "$PARQUET_FOUND"
    exit 1
fi
echo "PASS: Parquets are NOT tracked."

echo "[3] Running Coverage Gate Matrix..."
bash scripts/check_data_coverage.sh > /tmp/cov_check.log
if ! grep -q "OVERALL_STATUS=PASS" /tmp/cov_check.log; then
    echo "FAIL: Data coverage gating failed."
    cat /tmp/cov_check.log
    exit 1
fi
echo "PASS: Data coverage is healthy."
tail -n 6 /tmp/cov_check.log

echo "[4] Running Python compilation smoke testing..."
.venv/bin/python -m py_compile $(git ls-files '*.py') || {
    echo "FAIL: Syntax errors found in Python scripts."
    exit 1
}
echo "PASS: py_compile check successful."

echo "=========================================="
echo "    ALL PHASE 6 CONSTRAINTS PASSED        "
echo "=========================================="
exit 0
