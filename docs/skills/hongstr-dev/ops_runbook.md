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

## Data Freshness Profiles & Troubleshooting (SOP)

### Freshness Profiles
Freshness thresholds are applied based on the data source path:
1. **Realtime Feed** (`data/realtime/**`):
   - **OK**: <= 0.1h (6m)
   - **WARN**: <= 0.25h (15m)
   - **FAIL**: > 1.0h
2. **Backtest/Historical Feed** (`data/derived/**`):
   - **OK**: <= 26.0h (Daily ETL cycle + buffer)
   - **WARN**: <= 50.0h
   - **FAIL**: > 72.0h

### Troubleshooting Freshness = WARN
When `freshness` status is NOT OK, follow these steps to identify the root cause:

1. **Check MTime of the source file**:
   ```bash
   # For Realtime
   ls -l data/realtime/BTCUSDT/1m/klines.jsonl
   
   # For Backtest
   ls -l data/derived/BTCUSDT/1m/klines.jsonl
   ```

2. **Verify launchd job status**:
   - For Realtime: `launchctl print gui/$(id -u)/com.hongstr.realtime_ws`
   - For Backtest: `launchctl print gui/$(id -u)/com.hongstr.daily_etl`

3. **Check logs**:
   - Realtime: `tail -n 100 logs/realtime_ws.log`
   - ETL: `tail -n 100 logs/launchd_daily_etl.out.log`

4. **Identify Fault**:
   - **Realtime WARN**: Likely a websocket disconnect or `com.hongstr.realtime_ws` crash.
   - **Backtest WARN**: Daily ETL run at 02:00 AM failed or was skipped.
