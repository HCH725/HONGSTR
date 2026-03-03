# HONGSTR Operations: Skills Command Guide

This guide provides a list of copy-pasteable commands for calling the newly implemented skills via the Telegram Control Plane (tg_cp).

## 🟢 Telegram Control Plane (tg_cp) Skills

These skills can be invoked using the `/run <skill_name> <args>` pattern in the Telegram Control Plane.
Args can be passed in two formats:
- key/value pairs: `/run <skill> key=value key2=value2`
- JSON object: `/run <skill> {"key":"value","key2":2}`

### System Health & Monitoring (PR-A Series)

- **Morning Brief**: `/run system_health_morning_brief env=prod include_details=true`
- **Incident Timeline**: `/run incident_timeline_builder env=prod start="2026-02-25" end="2026-02-26"`
- **Config Drift**: `/run config_drift_auditor baseline_ref="origin/main" paths="src/hongstr, _local"`
- **Freshness Watchdog**: `/run data_freshness_watchdog_report env=prod`
- **Execution Quality (Skeleton)**: `/run execution_quality_report_readonly env=prod`

### Quant Specialist Skeletons (PR-B Series)

These skills are currently skeletons that return `UNKNOWN` unless the required research artifacts are present.

- **Backtest Reproducibility**: `/run backtest_reproducibility_audit backtest_id="BT_20260226_A" baseline_sha="abcd123"`
- **Factor Health**: `/run factor_health_and_drift_report factor_id="alpha_trend_v1"`
- **Strategy Sensitivity**: `/run strategy_regime_sensitivity_report strategy_id="trend_mvp_btc_1h"`

### Quant Skill Accepted Keys (SSOT)

For the three quant proxy skills, accepted keys are defined in `_local/telegram_cp/skills_registry.json`:

| Skill | Accepted Keys | Example |
|---|---|---|
| `backtest_reproducibility_audit` | `backtest_id`, `baseline_sha` | `/run backtest_reproducibility_audit backtest_id=BT_20260226_A baseline_sha=abcd123` |
| `factor_health_and_drift_report` | `factor_id` | `/run factor_health_and_drift_report factor_id=alpha_trend_v1` |
| `strategy_regime_sensitivity_report` | `strategy_id` | `/run strategy_regime_sensitivity_report strategy_id=trend_mvp_btc_1h` |

> Note: If `/run help <skill>` shows a generic example that does not match these keys, treat the schema keys above as authoritative until tg_cp help formatting is refreshed.

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
