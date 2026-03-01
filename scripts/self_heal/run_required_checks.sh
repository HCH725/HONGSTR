#!/usr/bin/env bash
set -euo pipefail
python_bin="./.venv/bin/python"
if [ ! -x "$python_bin" ]; then
  python_bin="python3"
fi
./scripts/guardrail_check.sh
if [ -f "tests/test_self_heal_allowed_paths.py" ]; then
  "$python_bin" -m pytest -q tests/test_self_heal_allowed_paths.py
else
  PYTHONPYCACHEPREFIX="${RUNNER_TEMP:-/tmp}/pycache" "$python_bin" -m py_compile scripts/self_heal/enforce_allowed_paths.py scripts/self_heal/parse_ticket.py
fi
