# Testing & Verification (Dev)

Policy SSOT: `docs/skills/global_red_lines.md`

## Runtime command invariant
- Use `./.venv/bin/python` for tests and scripts.
- Example:
  - `./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py`

## Required pre-PR checks
- Core untouched:
  - `git diff --name-only origin/main...HEAD | rg '^src/hongstr/'`
- No staged runtime artifacts:
  - `git status --porcelain | rg '^.. data/'`
- tg_cp no-exec guard:
  - `rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py`
- tg_cp local smoke:
  - `./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py`

Expected: all commands above return no blocking findings.
