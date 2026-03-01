#!/usr/bin/env bash
set -euo pipefail
./scripts/guardrail_check.sh
./.venv/bin/python -m pytest _local/telegram_cp/test_local_smoke.py
