> [!IMPORTANT] REFERENCE ONLY - Please see [Daily Report & Glossary](docs/ops/daily_report_zh.md) for current entry point.

# Ops Checklist — Kline Freshness (Realtime vs Backtest)

## Why
Backtest klines can tolerate delay (hours~days). Realtime signal klines cannot.

## Data Sources (SSOT)
- Canonical status: `data/state/system_health_latest.json`
- Freshness table: `data/state/freshness_table.json` (rows include `profile`)
- Producer: `bash scripts/refresh_state.sh` (State Plane)

## Profiles & Thresholds
### Realtime profile
- OK: <= 0.1h (6m)
- WARN: <= 0.25h (15m)
- FAIL: <= 1.0h

### Backtest profile
- OK: <= 26h
- WARN: <= 50h
- FAIL: <= 72h

## Ownership / Cadence (expected)
- Backtest klines: updated by Data Plane ETL job (daily cadence is acceptable)
- Realtime signals: updated by realtime service (continuous)

## Triage Steps
1) Run: `bash scripts/refresh_state.sh`
2) Check: `data/state/freshness_table.json` rows where status=WARN/FAIL
3) Confirm `profile`:
   - backtest WARN is usually non-urgent unless FAIL persists
   - realtime WARN/FAIL requires immediate investigation
4) If realtime is failing: inspect realtime service job + data/realtime paths
5) If backtest is failing: inspect ETL schedule + derived paths

## Guardrails
- Do not change `src/hongstr/**`
- Do not commit `data/**`
- tg_cp no-exec remains enforced
