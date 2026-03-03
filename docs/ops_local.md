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
  - **Retention**: Keep last 30 days by default (`RETENTION_DAYS=30`) and enforce a hard cap (`MAX_RUNS=1200`).

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

### Telegram 通知設定

在 repo root 建立 `.env`（從 `.env.example` 複製）：

```bash
cp .env.example .env
# edit .env
# TG_BOT_TOKEN=
# TG_CHAT_ID=
# TG_PARSE_MODE=Markdown
# TG_DISABLE=0
# TG_TIMEOUT=8
# TG_RETRIES=3
# TG_RETRY_BACKOFF_SEC=2
# TG_CONNECT_TIMEOUT=5
```

`scripts/load_env.sh` 會在執行時讀取 repo root `.env` 並 export。  
`notify_telegram.sh`、`daily_etl.sh`、`backfill_1m_from_2020.sh`、`recover_dashboard_full.sh`、`check_data_coverage.sh` 都會載入它。

`launchd` 也會在 command 內先 `source scripts/load_env.sh`，所以排程與手動執行使用同一份 `.env`。

你也可以手動等價做法（推薦在腳本內使用）：

```bash
set -a
[ -f .env ] && source .env
set +a
```

Launchd 注入有兩種方式：

1. 直接在 plist 的 `EnvironmentVariables` 設定 `TG_BOT_TOKEN` / `TG_CHAT_ID`。
2. 推薦：在 command 內 `source scripts/load_env.sh`，統一讀 repo root `.env`（目前模板使用這個方式）。

Telegram sanity 檢查（不輸出 token/chat id 原文）：

```bash
bash scripts/tg_sanity.sh
```

`notify_telegram.sh` retry/backoff 可透過 `.env` 調整：

- `TG_RETRIES`：重試次數（預設 `3`）
- `TG_RETRY_BACKOFF_SEC`：退避秒數基數（預設 `2`，實際 2/4/8...）
- `TG_CONNECT_TIMEOUT`：TCP connect timeout（預設 `5`）

DNS 不穩時，Telegram 通知會輸出 WARN 並跳過，不會阻斷 ETL/backfill/recovery 主流程。

### 報表去重（Control Plane Converge, Phase-1）

可用環境變數控制「重複摘要輸出」：

```bash
export HONGSTR_USE_CONTROL_PLANE_REPORTS=1
```

啟用後：

- `daily_etl.sh` / `backfill_1m_from_2020.sh` 仍會執行 `check_data_coverage.sh`（硬 gate 不變）
- 但會減少重複的長表格輸出，改由 control-plane/event 報表彙整
- `recover_dashboard_full.sh` 會跳過一次重複 healthcheck（`one_click_dashboard.sh` 已有硬性 healthcheck）

範例（只替換 `__REPO_ROOT__`，不把 TG secret 注入 plist）：

```bash
REPO_ROOT=/Users/hong/Projects/HONGSTR
mkdir -p ~/Library/LaunchAgents

sed \
  -e "s|__REPO_ROOT__|$REPO_ROOT|g" \
  "$REPO_ROOT/ops/launchagents/com.hongstr.daily_etl.plist" \
  > "$HOME/Library/LaunchAgents/com.hongstr.daily_etl.plist"

sed \
  -e "s|__REPO_ROOT__|$REPO_ROOT|g" \
  "$REPO_ROOT/ops/launchagents/com.hongstr.weekly_backfill.plist" \
  > "$HOME/Library/LaunchAgents/com.hongstr.weekly_backfill.plist"
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
- **Brake Healthcheck**: `./.venv/bin/python scripts/brake_healthcheck.py`

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
| `dashboard` | RunAtLoad + KeepAlive | Persistent local Streamlit UI (`127.0.0.1:8501`) | N/A |
| `realtime_ws` | Always On | Live feed & signal generation | 14d gzip, 45d deletion |
| `daily_etl` | 02:00 | Sync historical & derived data | N/A |
| `daily_healthcheck` | 02:30 | Verify system integrity | N/A |
| `retention_cleanup` | 03:00 | Disk space management | Keep runs for last 30 days (RETENTION_DAYS=30) + cap (MAX_RUNS=1200) |

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
bash scripts/healthcheck_dashboard.sh
```

Use `http://127.0.0.1:8501` in your browser.
(`localhost` may resolve to IPv6 `::1` first on macOS, which can be flaky in some setups.)

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

## Regime Performance (Regime Bucketing)

The system automatically segments backtest results into **BULL**, **BEAR**, and **NEUTRAL** regimes based on BTCUSDT 4h EMA signals.

1. **How to Generate**:
   Use `bash scripts/run_and_verify.sh`. It now automatically calls `scripts/generate_regime_report.py` after the backtest completes.

2. **Artifact**:
   Located at `data/backtests/<date>/<run_id>/regime_report.json`.

3. **Dashboard View**:
   Section **D. Regime Performance (Fixed 4h)** shows:
   - Aggregated metrics (Return, MDD, Sharpe) per regime.
   - Per-Symbol breakdown for BTC/ETH/BNB in each regime.

## Regime Quality Gate (Regime Strategy Acceptance)

The system evaluates backtest quality against predefined thresholds per regime.

1. **How to Generate**:
   Automatically generated by `bash scripts/run_and_verify.sh` after the backtest and regime report are ready.

2. **Artifact**:
   `data/backtests/<date>/<run_id>/gate.json`.

3. **Dashboard View**:
   Section **E. Gate (Regime Quality)** shows an overall **PASS/FAIL** and a detailed table of failures (e.g., low Sharpe or high MDD in a specific regime).

4. **CLI Verification**:

   ```bash
   # Find latest gate result
   ls -1dt data/backtests/*/*/gate.json | head -n 1
   # Print overall status
   python3 -c 'import json,glob,os; p=sorted(glob.glob("data/backtests/*/*/gate.json"), key=os.path.getmtime)[-1]; d=json.load(open(p)); print(p, d["results"]["overall"])'
   ```

## Automated Benchmark Suite (Full Loop)

To run a complete benchmark (FULL and SHORT runs) with consolidated reporting:

1. **Run Benchmark**:

   ```bash
   bash scripts/benchmark_suite.sh --symbols BTCUSDT,ETHUSDT,BNBUSDT
   ```

   This will execute `run_and_verify.sh` for both timeframes, generate all artifacts, and save the summary to `reports/benchmark_latest.json`.

2. **View CLI Report**:

   ```bash
   python3 scripts/report_benchmark.py
   ```

3. **Dashboard View**:
   Section **F. Benchmark (Latest)** displays a side-by-side comparison of FULL and SHORT results, including Gate status.

## Regime-Aware Optimization Persistence

The system persists the best parameters for each market regime (BULL, BEAR, NEUTRAL) in `optimizer_regime.json`.

1. **How to Generate**:
   Automatically generated by `bash scripts/run_and_verify.sh`.
   Manual trigger:

   ```bash
   python3 scripts/generate_optimizer_regime_artifact.py --run_dir <path_to_run>
   ```

2. **Artifact**:
   `data/backtests/<date>/<run_id>/optimizer_regime.json`.

3. **Dashboard View**:
   Section **G. Optimization (Regime-aware)** provides tabs for each regime with Top-K results and sample warnings.

4. **Selection API**:
   In Python, you can retrieve the best parameters for a specific market state:

   ```python
   from hongstr.selection.selection import get_best_params_for_regime
   params = get_best_params_for_regime("data/backtests/...", "BULL")
   ```

5. **CLI Check**:

   ```bash
   ls -1 data/backtests/*/*/optimizer_regime.json | tail -n 3
   ```

## Plan B: Auto PR + Auto Merge (No Team plan required)

If GitHub "Allow auto-merge" is locked, you can use GitHub CLI on your Mac to create PRs and request auto-merge:

```bash
brew install gh
gh auth login
bash scripts/gh_pr_merge.sh "chore: <title>" "<body>"
```
