> [!IMPORTANT] REFERENCE ONLY - Please see [Daily Report & Glossary](docs/ops/daily_report_zh.md) for current entry point.

# Audit Report: Kline Refresh Cadence & Split Feeds Recommendation

> REFERENCE ONLY


## 1) Job Distribution & Cadence

### Backtest Klines (Historical)

- **Primary Job**: `com.hongstr.daily_etl`
- **Cadence**: Daily at **02:00 AM**.
- **Script**: `scripts/daily_etl.sh` -> `scripts/ingest_historical.py` & `scripts/aggregate_data.py`.
- **Storage**: `data/derived/<SYMBOL>/<TF>/klines.jsonl`.
- **Nature**: Batch processing. Merges the last 3 days of historical data into the derived store once per day.

### Realtime Signal Inputs (Streaming)

- **Primary Job**: `com.hongstr.realtime_ws`
- **Cadence**: **Service (Continuous)**. Restarts automatically if it exits.
- **Script**: `scripts/run_realtime_service.sh` -> `scripts/run_ws.py`.
- **Storage**: `data/realtime/<SYMBOL>/<TF>/klines.jsonl` (and `aggTrade`).
- **Nature**: Streaming. Provides the "now" view for signal generation.

## 2) Current Threshold Audit

- **Current Settings**: `ok_h=12.0`, `warn_h=48.0` (Global).
- **Issue**: A 12-hour threshold is too loose for realtime signals (which should be minutes old) and potentially too tight for backtest klines if a single daily run is slightly delayed.

## 3) Proposed Thresholds (SSOT Freshness Profiles)

Rules are applied based on the file path of the source data:

| Profile | Path Pattern | OK (h) | WARN (h) | FAIL (h) |
| :--- | :--- | :--- | :--- | :--- |
| **Realtime** | `data/realtime/**` | <= 0.1 | <= 0.25 | > 1.0 |
| **Backtest** | `data/derived/**` | <= 26.0 | <= 50.0 | > 72.0 |

### Rationale

- **Realtime**: Signals must be current (within 6-15 minutes) to ensure execution alignment with market price.
- **Backtest**: Batch ETL runs daily at 02:00 AM. A 26-hour window allows for the 24-hour cycle plus a 2-hour buffer for processing jitter.

## 4) Implementation Detail (SOP for Logic)

If implementing in `scripts/state_snapshots.py`, use the following logic in the freshness loop:

```python
path_str = str(source_path)
if "data/realtime" in path_str:
    t_ok, t_warn = 0.1, 0.25
else:
    t_ok, t_warn = 26.0, 50.0

if age_h <= t_ok:
    status = "OK"
elif age_h <= t_warn:
    status = "WARN"
else:
    status = "FAIL"
```

### Data Synchronization

- **Target File**: [scripts/refresh_state.sh](file:///Users/hong/Projects/HONGSTR/scripts/refresh_state.sh)
- **Change**: Ensure `refresh_state.sh` (which runs hourly) pulls metadata from both `data/derived` and `data/realtime`.

## 5) Preflight Verification

- **Core Diff**: 0 (No code changed during this audit).
- **Command**: `git diff main` shows no modifications to `src/hongstr`.
