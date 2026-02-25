# Ops Runbook (Dev)

**MUST READ FIRST:** `docs/skills/global_red_lines.md`

## launchd restart pattern (avoid Telegram 409 / multi-instance)
- Preferred: `bootout -> sleep -> bootstrap -> verify pid/active count`

## tg_cp cache hygiene
- If outputs look stale: remove cache files under `data/state/_tg_cp/` (keep session_state.json if desired)
- Restart tg_cp via launchd pattern above.

## SSOT state refresh
- Run `bash scripts/refresh_state.sh`
- Verify key SSOT files exist (untracked):
  - `data/state/freshness_table.json`
  - `data/state/coverage_matrix_latest.json`
  - `data/state/brake_health_latest.json`
  - `data/state/regime_monitor_latest.json`
  - `data/state/execution_mode.json`
  - `data/state/services_heartbeat.json`

## Dashboard
- Dashboard should read SSOT from `data/state/*` (not recompute dynamically).
