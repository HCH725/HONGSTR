# HONGSTR LaunchAgents

This directory contains macOS `launchd` configuration files (plists) for automating local operations.

## Plist Index

| Label | Command | Schedule / Behavior |
| :--- | :--- | :--- |
| `com.hongstr.dashboard` | `streamlit run scripts/dashboard.py --server.address 127.0.0.1 --server.port 8501` | RunAtLoad + KeepAlive |
| `com.hongstr.realtime_ws` | `scripts/run_realtime_service.sh` | RunAtLoad + KeepAlive |
| `com.hongstr.daily_etl` | `scripts/daily_etl.sh` | 02:00 Daily |
| `com.hongstr.refresh_state` | `scripts/refresh_state.sh` | RunAtLoad + Every 60m |
| `com.hongstr.daily_healthcheck` | `scripts/refresh_state.sh` (alias) | 02:30 Daily |
| `com.hongstr.weekly_backfill` | `scripts/backfill_1m_from_2020.sh` | Sunday 03:30 |
| `com.hongstr.retention_cleanup` | `scripts/retention_cleanup.sh` | 03:00 Daily |

## 3-Plane Ownership (Actionable)

| Label | Plane | Unique responsibility |
| :--- | :--- | :--- |
| `com.hongstr.daily_etl` | Data | Refresh ETL/derived inputs only. |
| `com.hongstr.weekly_backfill` | Data | Backfill historical data gaps only. |
| `com.hongstr.retention_cleanup` | Data | Run retention cleanup only. |
| `com.hongstr.daily_backtest` | Data | Produce backtest artifacts only. |
| `com.hongstr.refresh_state` | State | Canonical SSOT scheduler (`refresh_state.sh` -> `state_snapshots.py`). |
| `com.hongstr.daily_healthcheck` | State (alias) | Compatibility alias that calls `refresh_state.sh` only. |
| `com.hongstr.dashboard` | Control | Read-only dashboard from SSOT state. |
| `com.hongstr.tg_cp` | Control | Read-only Telegram control-plane from SSOT state. |
| `com.hongstr.realtime_ws` | Control | Keep realtime service alive (non-SSOT publisher). |
| `com.hongstr.research_poller` | Control (queue) | Queue/de-dup/cooldown only, report_only. |
| `com.hongstr.research_loop` | Control (runner) | Execute report-only research loop jobs only. |

Notes:
- `research_poller`/`research_loop` may be deployed as local LaunchAgents outside this template folder; they are still non-SSOT publishers.
- No job outside State Plane should publish canonical `data/state/*` snapshots.

## Deployment Note

These files contain a `__REPO_ROOT__` placeholder. **Do not copy them directly to `~/Library/LaunchAgents`**.

Use the deployment instructions in [`docs/ops_local.md`](../../docs/ops_local.md) to replace the placeholder with your absolute repository path.

### Telegram via `.env`

`com.hongstr.daily_etl.plist` and `com.hongstr.weekly_backfill.plist` execute:

- `source scripts/load_env.sh`
- then run ETL/backfill script

This allows both interactive shell and launchd jobs to share the same repo-root `.env` without storing secrets in plist templates.

`com.hongstr.refresh_state.plist` is the canonical State Plane orchestrator for SSOT snapshots.
`com.hongstr.daily_healthcheck.plist` is intentionally kept as a compatibility alias to trigger the same `refresh_state` flow at the legacy daily schedule.

### Overlap Checklist + Deprecation Path

- `refresh_state` is the only canonical State Plane scheduler for SSOT publication.
- `daily_healthcheck` must remain alias-only and must not gain independent state logic.
- `research_poller` (queue) and `research_loop` (runner) stay split by responsibility.

Deprecation path for `daily_healthcheck`:
1. Keep alias behavior only (current).
2. Stop adding new logic under healthcheck alias.
3. Disable/remove alias schedule after stable observation period.
4. Rollback by re-enabling alias plist if needed.

## Migration SOP (bootout -> wait -> bootstrap)

Apply plist updates with this sequence to avoid duplicate instances and Telegram 409 conflicts:

```bash
LABEL="com.hongstr.<job>"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
sleep 5
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl print "gui/$(id -u)/$LABEL" | rg 'state =|pid =|last exit|active count|program|ProgramArguments'
```

Single-instance verification example (`tg_cp`):

```bash
launchctl print "gui/$(id -u)/com.hongstr.tg_cp" | rg 'state =|pid =|active count'
pgrep -af "tg_cp_server.py"
```

## Log Files

Output and error logs are redirected to the project `logs/` directory:

- `logs/launchd_<label>.out.log`
- `logs/launchd_<label>.err.log`
