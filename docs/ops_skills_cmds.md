# HONGSTR Operations: Skills Command Guide

This guide provides a list of copy-pasteable commands for calling the newly implemented skills via the Telegram Control Plane (tg_cp).

## 🟢 Telegram Control Plane (tg_cp) Skills

These skills can be invoked using the `/run <skill_name> <args>` pattern in the Telegram Control Plane.
Args support both formats:
- key/value pairs: `/run <skill> key=value key2=value2`
- JSON object: `/run <skill> {"key":"value","key2":2}`
- Inspect exact schema/keys/examples:
  - `/run help <skill>`
  - `/skills help <skill>`

### System Health & Monitoring (PR-A Series)

- **Morning Brief**: `/run system_health_morning_brief env=prod include_details=true`
- **Incident Timeline**: `/run incident_timeline_builder env=prod start="2026-02-25" end="2026-02-26"`
- **Config Drift**: `/run config_drift_auditor baseline_ref="origin/main" paths="src/hongstr, _local"`
- **Freshness Watchdog**: `/run data_freshness_watchdog_report env=prod`
- **Execution Quality (Skeleton)**: `/run execution_quality_report_readonly env=prod`

### Quant Specialist Skeletons (PR-B Series)

These skills are currently skeletons that return `UNKNOWN` unless the required research artifacts are present.

- **Backtest Reproducibility**:
  - key=value: `/run backtest_reproducibility_audit strategy_id=trend_mvp_btc_1h runs=3 report_only=true`
  - JSON: `/run backtest_reproducibility_audit {"strategy_id":"trend_mvp_btc_1h","runs":3,"report_only":true}`
- **Factor Health**:
  - key=value: `/run factor_health_and_drift_report factor_id=factor_alpha report_only=true`
  - JSON: `/run factor_health_and_drift_report {"factor_id":"factor_alpha","report_only":true}`
- **Strategy Sensitivity**:
  - key=value: `/run strategy_regime_sensitivity_report strategy_id=trend_mvp_btc_1h report_only=true`
  - JSON: `/run strategy_regime_sensitivity_report {"strategy_id":"trend_mvp_btc_1h","report_only":true}`
- **Schema Help**:
  - `/run help backtest_reproducibility_audit`
  - `/skills help backtest_reproducibility_audit`

When args are invalid (for example unknown keys), tg_cp response includes:
- `allowed_keys`
- `example_command`
- `example_json`
- `refresh_hint`

---

## 📂 SSOT Artifact Requirements

To transition a skill from `UNKNOWN` to `OK`, the following SSOT files must be present and readable in `data/state/` or `reports/research/`:

| Skill | Required SSOT File / Path |
|-------|---------------------------|
| `system_health_morning_brief` | `data/state/system_health_latest.json` |
| `incident_timeline_builder` | `data/state/system_health_latest.json` (or component files) |
| `data_freshness_watchdog_report` | `data/state/freshness_table.json` |
| `execution_quality_report_readonly` | `data/state/execution_quality_latest.json` |
| `backtest_reproducibility_audit` | `reports/research/**/*reproducibility.json` |
| `factor_health_and_drift_report` | `reports/research/factors/factor_health_<id>.json` |
| `strategy_regime_sensitivity_report` | `reports/research/sensitivity/sensitivity_<id>.json` |

---

## 🛡️ Guardrail Status

- **Core Invariant**: All skills are READ-ONLY.
- **No-Exec**: No `subprocess`, `os.system`, or `Popen` calls in `tg_cp`.
- **SSOT-Only**: Data is pulled exclusively from canonical state/research files.
