# HONGSTR Operations: tg_cp Skills Command Guide

Use `/skills` to list skills, and `/run help <skill_name>` to inspect the live schema.

All examples below are aligned to `_local/telegram_cp/skills_registry.json`.

## /run Examples (Schema-Aligned)

- `status_overview`
  - `/run status_overview include_sources=true`
- `logs_tail_hint`
  - `/run logs_tail_hint lines=60`
- `brake_status`
  - `/run brake_status`
- `incident_timeline_builder`
  - `/run incident_timeline_builder start=2026-02-26T00:00:00Z end=2026-02-26T06:00:00Z env=prod`
  - `/run incident_timeline_builder start=2026-02-26T00:00:00Z end=2026-02-26T06:00:00Z env=prod keywords=latency,regime services=tg_cp,dashboard`
- `signal_leakage_audit`
  - `/run signal_leakage_audit artifact_path=research/audit/tests/fixtures/clean.json max_lookahead_ms=0`
- `system_health_morning_brief`
  - `/run system_health_morning_brief env=prod include_details=true`
- `config_drift_auditor`
  - `/run config_drift_auditor baseline_ref=origin/main paths=src/hongstr,_local/telegram_cp`
- `data_freshness_watchdog_report`
  - `/run data_freshness_watchdog_report env=prod`
- `execution_quality_report_readonly`
  - `/run execution_quality_report_readonly env=prod`
- `signal_leakage_and_lookahead_audit`
  - `/run signal_leakage_and_lookahead_audit artifact_path=research/audit/tests/fixtures/clean.json max_lookahead_ms=0`
- `backtest_reproducibility_audit`
  - `/run backtest_reproducibility_audit backtest_id=BT_20260226_A baseline_sha=abcd1234`
- `factor_health_and_drift_report`
  - `/run factor_health_and_drift_report factor_id=alpha_trend_v1`
- `strategy_regime_sensitivity_report`
  - `/run strategy_regime_sensitivity_report strategy_id=trend_mvp_btc_1h`

## SSOT Artifact Expectations

- `system_health_morning_brief`: `data/state/system_health_latest.json`
- `incident_timeline_builder`: `data/state/system_health_latest.json` (or fallback component files)
- `data_freshness_watchdog_report`: `data/state/freshness_table.json`
- `execution_quality_report_readonly`: `data/state/execution_quality_latest.json`
- `backtest_reproducibility_audit`: `reports/research/**/*reproducibility.json`
- `factor_health_and_drift_report`: `reports/research/factors/factor_health_<id>.json`
- `strategy_regime_sensitivity_report`: `reports/research/sensitivity/sensitivity_<id>.json`

## Guardrails

- `read_only` / `report_only` only
- tg_cp no-exec (`subprocess`, `os.system`, `Popen` disallowed in tg_cp server)
- SSOT-only data access
