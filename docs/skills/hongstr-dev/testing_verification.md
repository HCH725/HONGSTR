# Testing & Verification (Dev)

**MUST READ FIRST:** `docs/skills/global_red_lines.md`

## Always verify
- `git diff --name-only origin/main...HEAD | rg '^src/hongstr/'` must be empty.
- `git status --porcelain | rg '^.. data/'` must be empty (no staged data artifacts).
- Guardrail scan for tg_cp: ensure no subprocess/os.system/Popen introduced.

## Smoke tests (local)
- `./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py` (if present)
