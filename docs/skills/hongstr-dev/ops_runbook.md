# Ops Runbook (Dev)

Policy SSOT: `docs/skills/global_red_lines.md`

## Runtime invariant
- Use `./.venv/bin/python` for all Python commands.
- Do not assume `python` binary exists on `PATH`.

## State Plane refresh
- Canonical refresh command:
  - `bash scripts/refresh_state.sh`
- Canonical writer boundary:
  - `scripts/state_snapshots.py` writes `data/state/*`

## launchd ownership
- Canonical State Plane scheduler: `com.hongstr.refresh_state`
- Legacy alias/deprecation path: `com.hongstr.daily_healthcheck` (`02:30`) triggers refresh chain only.
- `daily_healthcheck` must not own independent state computation/publishing.

## SSOT-only status behavior
- tg_cp/dashboard top-level status must read SSOT only.
- If SSOT missing/unreadable, degrade to:
  - `SSOT_STATUS: UNKNOWN`
  - `refresh_hint: bash scripts/refresh_state.sh`

## tg_cp cache hygiene
- If response looks stale, clear cache files under `data/state/_tg_cp/` (optional: keep `session_state.json`).
- Restart tg_cp with launchd sequence:
  - `bootout -> sleep -> bootstrap -> verify state/pid/active count`
