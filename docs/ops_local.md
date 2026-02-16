# HONGSTR Local Operations Guide (macOS)

This guide covers how to set up HONGSTR as background services on a local Mac mini using macOS `launchd`.

## Prerequisites

1. **Python Environment**: Ensure a virtual environment exists at the project root.

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2. **Environment Variables**: Create and configure `.env`.

    ```bash
    cp .env.example .env
    # Edit .env with your Binance keys and preferences
    ```

## Installation

The project uses placeholders in LaunchAgent plists. Follow these steps to install them for the current user.

```bash
# 1. Create target directory
mkdir -p ~/Library/LaunchAgents

# 2. Replace __REPO_ROOT__ with current path and copy to LaunchAgents
# One-liner to deploy all plists:
REPO_ROOT=$(pwd)
for f in ops/launchagents/*.plist; do
    name=$(basename "$f")
    sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$f" > ~/Library/LaunchAgents/"$name"
done

# 3. Load the services
# Note: In macOS, bootstrapping loads and starts the service if RunAtLoad=true
for f in ~/Library/LaunchAgents/com.hongstr.*.plist; do
    launchctl bootstrap gui/$(id -u) "$f"
done
```

## Service Management

### Check Status

```bash
# List all HONGSTR jobs
launchctl list | grep hongstr
```

### Stop / Unload Services

```bash
# To stop and unload all
for f in ~/Library/LaunchAgents/com.hongstr.*.plist; do
    launchctl bootout gui/$(id -u) "$f"
done
```

### Manual Execution (Without launchd)

If you want to run the scripts manually to test:

```bash
# Realtime WS
bash scripts/run_realtime_service.sh

# ETL
bash scripts/daily_etl.sh

# Healthcheck
bash scripts/daily_backtest_healthcheck.sh

# Cleanup
bash scripts/retention_cleanup.sh
```

## Logs & Data

- **Background Logs**: `logs/launchd_<job_name>.out.log` and `logs/launchd_<job_name>.err.log`.
- **Application Logs**:
  - `logs/realtime_ws.log`: Continuous WS feed.
  - `logs/daily_etl.log`: Ingestion/Aggregation results.
  - `logs/daily_healthcheck.log`: Backtest verification details.
- **Reporting**: `data/reports/daily_backtest_health.csv` (Daily performance check).

## Job Schedule & Lifecycle

| Job Name | Schedule | Purpose | Retention Policy |
| :--- | :--- | :--- | :--- |
| `realtime_ws` | Always On | Live feed & signal generation | 14d gzip, 45d deletion |
| `daily_etl` | 02:00 | Sync historical & derived data | N/A |
| `daily_healthcheck` | 02:30 | Verify system integrity | N/A |
| `retention_cleanup` | 03:00 | Disk space management | Keep latest 50 runs |

## Verification & PKG-4 Commands

After deployment, you can verify everything is working with:

```bash
# Run the automated verification script
chmod +x scripts/verify_local_services.sh
./scripts/verify_local_services.sh
```

### Deep Inspection

If a service shows a non-zero exit code in `launchctl list`, use:

```bash
# Print detailed state of a job
launchctl print gui/$(id -u)/com.hongstr.realtime_ws

# Check launchd-specific logs
tail -f logs/launchd_realtime_ws.err.log
```

## Common Issues & Troubleshooting

1. **"Already bootstrapped"**: If you updated a plist, you must `bootout` before `bootstrap` again.
2. **$PATH issues**: Launchd has a minimal PATH. The plists explicitly set `/usr/local/bin:/usr/bin:/bin`, but if your `python3` or `git` is elsewhere, you may need to edit the `EnvironmentVariables` in the `.plist`.
3. **Permissions**: Ensure all scripts are executable: `chmod +x scripts/*.sh`.
4. **Data Missing**: If healthcheck fails, verify `data/derived/` contains klines. Run `bash scripts/daily_etl.sh` manually once to prime the data.
