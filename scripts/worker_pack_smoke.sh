#!/usr/bin/env bash
# HONGSTR Worker Pack Smoke Test
# Runs red-line checks locally on the worker, verifies python structure, and tests SSH connectivity.
set -euo pipefail

echo "== HONGSTR Worker Pack Smoke Test =="

SCRIPT_DIR=$(dirname "$0")
REPO_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$REPO_DIR"

# Source the env vars if present
if [ -f ".env.worker" ]; then
  source .env.worker
fi

# 1. Red Line Guards Check (Must pass locally)
echo "=> Checking Red Line Guards..."

if git diff --name-only origin/main...HEAD | grep '^src/hongstr/' > /dev/null; then
  echo "!! FAIL: Core engine (src/hongstr/) has been modified."
  exit 1
fi

if grep -n -E 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py > /dev/null 2>&1; then
  echo "!! FAIL: Forbidden exec calls found in tg_cp_server.py."
  exit 1
fi

if git status --porcelain | grep '^.. data/' > /dev/null; then
  echo "!! FAIL: data/ artifacts are staged or tracked."
  exit 1
fi
echo "=> Red Lines: PASS"

# 2. Python Environment & Import Check
echo "=> Checking Python Environment..."
if [ ! -f "./.venv/bin/python" ]; then
  echo "!! FAIL: Virtual environment not found. Run bootstrap script first."
  exit 1
fi

# We run the basic smoke test to ensure things parse correctly
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
./.venv/bin/python -m pytest -q research/loop/tests
echo "=> Python tests: PASS"

# 3. Connection Check (if configured)
if [ -n "${HONGSTR_MAIN_HOST:-}" ] && [ -n "${HONGSTR_MAIN_SSH_USER:-}" ]; then
  echo "=> Testing SSH connectivity to ${HONGSTR_MAIN_SSH_USER}@${HONGSTR_MAIN_HOST}..."
  if ssh -q -o BatchMode=yes -o ConnectTimeout=5 "${HONGSTR_MAIN_SSH_USER}@${HONGSTR_MAIN_HOST}" "echo 'SSH Connection successful'"; then
    echo "=> SSH Test: PASS"
    
    # Dummy rsync test
    echo "=> Testing Dummy rsync..."
    touch /tmp/worker_smoke_test.txt
    if rsync -avz --timeout=10 /tmp/worker_smoke_test.txt "${HONGSTR_MAIN_SSH_USER}@${HONGSTR_MAIN_HOST}:${HONGSTR_MAIN_DEST}/worker_smoke_test.txt"; then
      echo "=> rsync Test: PASS"
    else
      echo "!! FAIL: rsync test failed. Check permissions on ${HONGSTR_MAIN_DEST} at destination."
    fi
    rm -f /tmp/worker_smoke_test.txt
  else
    echo "!! FAIL: SSH Connection timed out or failed. Check key config and Tailscale status."
  fi
else
  echo "=> Skipping SSH connectivity check: Main Host variables not set in .env.worker."
fi

echo "== Smoke Test Complete =="
