#!/usr/bin/env bash
# HONGSTR Worker Pack: Run Once execution script
# Executed periodically by launchd. Handles venv activation, computation, and sync.
set -euo pipefail

SCRIPT_DIR=$(dirname "$0")
REPO_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$REPO_DIR"

if [ -f ".env.worker" ]; then
  source .env.worker
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Worker Execution Started"

# 1. Ensure up to date from main (Fast-Forward only)
# By default, workers should operate on the latest canonical research codebase.
git fetch origin main -q
git merge origin/main --ff-only -q || {
  echo "[WARN] Unable to fast-forward local branch. Continuing with current code."
}

if [ ! -f "./.venv/bin/python" ]; then
  echo "[FATAL] Virtual environment not found. Please run bootstrap."
  exit 1
fi

# 2. Dummy / Light execution
# In a real environment, this invokes the multi-strategy research/backtest runner
echo "=> Running research computations..."
# e.g., ./.venv/bin/python -m research.loop.runner --role="${HONGSTR_WORKER_ROLE:-research}"

# 3. Synchronize outputs back to Main Host
if [ -n "${HONGSTR_MAIN_HOST:-}" ] && [ -n "${HONGSTR_MAIN_SSH_USER:-}" ]; then
  echo "=> Syncing data back to Main Host..."
  # Rsync the backtests outputs. The worker creates report_only non-tracked artifacts.
  rsync -avz --ignore-existing --timeout=10 "data/backtests/" "${HONGSTR_MAIN_SSH_USER}@${HONGSTR_MAIN_HOST}:${HONGSTR_MAIN_DEST}/" || {
    echo "[ERROR] Rsync to Main Host failed."
    # We do NOT exit 1 here, so the next batch attempts again without halting the scheduler loop entirely.
  }
else
  echo "[INFO] No Main Host configured. Computations remain local."
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Worker Execution Complete"
