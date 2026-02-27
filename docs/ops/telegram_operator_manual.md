# Telegram Operator Manual (HONGSTR)

## 1. Daily Report Command

- Command: `/daily` (alias: `/report_daily`)
- Data source (single SSOT): `data/state/daily_report_latest.json`
- Output behavior:
  - Preferred: LLM partner-readable rendering (5 sections)
  - Guaranteed: deterministic fallback text (same 5 sections, no invented numbers)
  - If LLM timeout/failure: fallback is returned with `DAILY_REPORT_STATUS: WARN` and `RefreshHint`

### /daily 5 sections

1. System Overview (`SSOT`, Single Source of Truth)
2. Freshness summary (`Freshness`)
3. Strategy & backtest summary (`OOS`, `Sharpe`, `MDD`)
4. Governance summary (`Overfit gates` policy version + today's gate counts)
5. Guardrails summary (`report_only`, `actions_empty`, preflight-expected checks)

## 2. Other Common Commands

- `/status`: system health quick summary
- `/freshness`: freshness matrix details
- `/regime`: regime monitor summary
- `/ml_status`: ML pipeline summary
- `/skills`: list available read-only skills
- `/run help <skill_name>`: show exact args schema

## 3. Change Daily Report Schedule (launchd)

The daily report content is published by state-plane refresh (`scripts/refresh_state.sh` -> `scripts/state_snapshots.py`).

- Launchd label placeholder: `com.hongstr.refresh_state`
- Example operations (replace label if your environment differs):
  - `launchctl print gui/$(id -u)/com.hongstr.refresh_state`
  - update the corresponding plist schedule (`StartCalendarInterval`)
  - `launchctl bootout ...` then `launchctl bootstrap ...` to reload

## 4. Troubleshooting (SSOT missing/unreadable)

If `/daily` shows `missing_daily_report_ssot` or `unreadable_daily_report_ssot`:

1. Run refresh: `bash scripts/refresh_state.sh`
2. Confirm file exists: `data/state/daily_report_latest.json`
3. Confirm producer health: `data/state/system_health_latest.json`
4. Retry `/daily`

If still failing, inspect:

- `logs/launchd_daily_etl.out.log`
- `logs/launchd_dashboard.out.log`
- `data/state/_tg_cp/runtime.log`

---
Safety statement: `core diff=0 | tg_cp no-exec | report_only`
