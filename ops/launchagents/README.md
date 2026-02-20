# HONGSTR LaunchAgents

This directory contains macOS `launchd` configuration files (plists) for automating local operations.

## Plist Index

| Label | Command | Schedule / Behavior |
| :--- | :--- | :--- |
| `com.hongstr.realtime_ws` | `scripts/run_realtime_service.sh` | RunAtLoad + KeepAlive |
| `com.hongstr.daily_etl` | `scripts/daily_etl.sh` | 02:00 Daily |
| `com.hongstr.daily_healthcheck` | `scripts/daily_backtest_healthcheck.sh` | 02:30 Daily |
| `com.hongstr.weekly_backfill` | `scripts/backfill_1m_from_2020.sh` | Sunday 03:30 |
| `com.hongstr.retention_cleanup` | `scripts/retention_cleanup.sh` | 03:00 Daily |

## Deployment Note

These files contain a `__REPO_ROOT__` placeholder. **Do not copy them directly to `~/Library/LaunchAgents`**.

Use the deployment instructions in [`docs/ops_local.md`](../../docs/ops_local.md) to replace the placeholder with your absolute repository path.

### Telegram via `.env`

`com.hongstr.daily_etl.plist` and `com.hongstr.weekly_backfill.plist` now execute:

- `source scripts/load_env.sh`
- then run ETL/backfill script

This allows both interactive shell and launchd jobs to share the same repo-root `.env` without storing secrets in plist templates.

## Log Files

Output and error logs are redirected to the project `logs/` directory:

- `logs/launchd_<label>.out.log`
- `logs/launchd_<label>.err.log`
