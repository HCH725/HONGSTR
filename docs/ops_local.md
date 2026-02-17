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

### Quick Verify One-Liner (Recommended)

To run a backtest (2023-2024, BTC/ETH/BNB, 1h+4h) and automatically verify results upon completion:

```bash
# Foreground (default)
./scripts/run_and_verify.sh --symbols BTCUSDT,ETHUSDT,BNBUSDT --start 2023-01-01 --end 2024-02-01

# Background (async wait up to 20m)
./scripts/run_and_verify.sh --mode background --symbols BTCUSDT,ETHUSDT,BNBUSDT --start 2023-01-01 --end 2024-02-01
```

### Backtest Quality Gate

The `run_and_verify.sh` script now includes an automatic quality gate check (`scripts/gate_summary.py`).
It verifies the following criteria for BTC/ETH/BNB (1h & 4h):

| Timeframe | Metric | Fail Threshold | Soft Goal |
| --- | --- | --- | --- |
| Any | Trades | < 30 | - |
| Any | Max Drawdown | <= -25% | > -15% |
| Any | Exposure | > 98% | - |
| Any | Sharpe | < -0.2 | > 0.5 |

**Manual Gate Check**:

```bash
export LATEST_DIR="$(bash scripts/get_latest_completed_dir.sh)"
./.venv/bin/python scripts/gate_summary.py --dir "$LATEST_DIR"
```

### Explicit Verification Output

`verify_latest.py` now explicitly checks for the presence of `BTCUSDT`, `ETHUSDT`, and `BNBUSDT` keys in the summary. If any are missing, it will print `MISSING` and exit with an error code.

### Local Monitoring Dashboard

Monitor system health, data freshness, and strategy details (Regime/Selection) via a local Streamlit app.

```bash
./scripts/run_dashboard.sh
```

This will open `http://localhost:8501` in your browser.

**Features**:

- **Environment Control**: Execution mode, service heartbeats, and data freshness checks (1m klines).
- **HONG Detail**: Current Regime (fixed 4h source), Strategy Selection, and detailed Backtest Performance (switchable 1h/4h).
- **Auto-Refresh**: Updates every 10s (toggle in sidebar).

**Troubleshooting**:

- If `ModuleNotFoundError: No module named 'streamlit'`, run `./scripts/run_dashboard.sh` again (it auto-installs dependencies).
- Metrics or Regime showing "MISSING": Ensure `data/derived/...` and `data/state` artifacts exist.

```bash
launchctl print gui/$(id -u)/com.hongstr.realtime_ws
tail -f logs/launchd_realtime_ws.err.log
```

**Execution Mode**:

- Defaults to `LOCAL`.
- Shows `LOCAL_SERVICES` if state files exist in `data/state` or `logs/`.
- Override via `export HONGSTR_EXEC_MODE=PAPER`.

## Common Issues & Troubleshooting

1. **WS Connected but no files?**: Run `bash scripts/watch_realtime.sh` to check if logs show "WebSocket connected" and if files in `data/realtime` are growing.
2. **Derived data missing?**: Run `bash scripts/check_data_paths.sh`. If it shows missing files, run `bash scripts/daily_etl.sh` manually.
3. **Permissions**: Ensure scripts are executable: `chmod +x scripts/*.sh`.

## Benchmark Reporting

To generate and view the latest benchmark report (FULL vs SHORT):

1. **Run Benchmark Suite** (Runs backtests + generates `reports/benchmark_latest.json`):

   ```bash
   bash scripts/benchmark_suite.sh
   # Or manually:
   # bash scripts/run_backtest.py ...
   # python scripts/report_benchmark.py
   ```

2. **View in Dashboard**:
   - Open Dashboard: `./scripts/run_dashboard.sh`
   - Scroll to **Section C. Benchmark** to see the comparison table.
