# HONGSTR Local Operations Guide (macOS)

This guide covers how to set up HONGSTR as background services on a local Mac mini using macOS `launchd`.

## Data Architecture & Lifecycle

HONGSTR relies on a clear distinction between realtime and historical data:

- **Raw Data (`data/realtime/`)**:
  - **Source**: Captured from Binance WS by `realtime_ws` service.
  - **Purpose**: Low-latency signal generation and live execution.
  - **Retention**: Kept for 14 days; compressed (gzip) until 45 days, then deleted.
- **Derived Data (`data/derived/`)**:
  - **Source**: Processed from 1m klines via `daily_etl` service.
  - **Purpose**: **Offline Backtesting**. All resampling (5m, 1h, etc.) happens from here.
  - **Retention**: Persistent primary historical source.
- **Backtest Runs (`data/backtests/`)**:
  - **Retention**: Deleted after 90 days or if total runs exceed 50.

## Installation / Quickstart

1. **Deploy Plists**:

    ```bash
    mkdir -p ~/Library/LaunchAgents
    REPO_ROOT=$(pwd)
    for f in ops/launchagents/*.plist; do
        sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$f" > ~/Library/LaunchAgents/$(basename "$f")
    done
    ```

2. **Bootstrap Services**:

    ```bash
    for f in ~/Library/LaunchAgents/com.hongstr.*.plist; do
        launchctl bootstrap gui/$(id -u) "$f" 2>/dev/null || launchctl enable gui/$(id -u)/$(basename "$f" .plist)
    done
    ```

## Service Management

### Check Status

```bash
# List all HONGSTR jobs
launchctl list | grep hongstr
```

### Observability Tools

We provide specialized scripts for monitoring:

- **Watch Realtime**: `bash scripts/watch_realtime.sh --symbol BTCUSDT --lines 20`
- **Check Data Paths**: `bash scripts/check_data_paths.sh`

### Manual Execution

```bash
bash scripts/run_realtime_service.sh
bash scripts/daily_etl.sh
bash scripts/daily_backtest_healthcheck.sh
bash scripts/retention_cleanup.sh
```

## Logs & Data

- **Background Logs**: `logs/launchd_<job_name>.out.log`
- **Application Logs**: `logs/realtime_ws.log`, `logs/daily_etl.log`
- **Health Reports**: `data/reports/daily_backtest_health.csv`

## Job Schedule & Lifecycle

| Job Name | Schedule | Purpose | Retention Policy |
| :--- | :--- | :--- | :--- |
| `realtime_ws` | Always On | Live feed & signal generation | 14d gzip, 45d deletion |
| `daily_etl` | 02:00 | Sync historical & derived data | N/A |
| `daily_healthcheck` | 02:30 | Verify system integrity | N/A |
| `retention_cleanup` | 03:00 | Disk space management | Keep latest 50 runs |

## Verification & PKG-4 Commands

```bash
chmod +x scripts/verify_local_services.sh
./scripts/verify_local_services.sh
```

### Verify latest completed backtest

To instantly verify the latest *completed* backtest (skipping running ones):

```bash
export LATEST_DIR="$(bash scripts/get_latest_completed_dir.sh)"; ./.venv/bin/python scripts/verify_latest.py
```

To wait for the latest run to complete (timeout 20m) and then verify:

```bash
end=$((SECONDS+1200)); while [ $SECONDS -lt $end ]; do L=$(ls -1dt data/backtests/*/* 2>/dev/null | head -n 1); if [ -f "$L/summary.json" ]; then export LATEST_DIR="$L"; break; fi; sleep 5; done; ./.venv/bin/python scripts/verify_latest.py
```

### Deep Inspection

If a service fails:

```bash
launchctl print gui/$(id -u)/com.hongstr.realtime_ws
tail -f logs/launchd_realtime_ws.err.log
```

## Common Issues & Troubleshooting

1. **WS Connected but no files?**: Run `bash scripts/watch_realtime.sh` to check if logs show "WebSocket connected" and if files in `data/realtime` are growing.
2. **Derived data missing?**: Run `bash scripts/check_data_paths.sh`. If it shows missing files, run `bash scripts/daily_etl.sh` manually.
3. **Permissions**: Ensure scripts are executable: `chmod +x scripts/*.sh`.
