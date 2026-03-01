#!/usr/bin/env bash
set -euo pipefail
./scripts/guardrail_check.sh
if [ -x "./.venv/bin/python" ]; then
  ./.venv/bin/python -m pytest _local/telegram_cp/test_local_smoke.py
else
  python3 -m pytest _local/telegram_cp/test_local_smoke.py
fi
