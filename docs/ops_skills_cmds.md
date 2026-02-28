# HONGSTR Operations: Skills Command Guide

This guide provides a list of copy-pasteable commands for calling the newly implemented skills via the Telegram Control Plane (tg_cp).

## 🟢 Telegram Control Plane (tg_cp) Skills

These skills can be invoked using the `/run <skill_name> <args>` pattern in the Telegram Control Plane.

### System Health & Monitoring (PR-A Series)

- **Morning Brief**: `/run system_health_morning_brief env=prod include_details=true`
- **Incident Timeline**: `/run incident_timeline_builder env=prod start="2026-02-25" end="2026-02-26"`
- **Config Drift**: `/run config_drift_auditor baseline_ref="origin/main" paths="src/hongstr, _local"`
- **Freshness Watchdog**: `/run data_freshness_watchdog_report env=prod`
- **Execution Quality (Skeleton)**: `/run execution_quality_report_readonly env=prod`

### Quant Specialist Skeletons (PR-B Series)

These skills stay `report_only`; they degrade to `WARN`/`UNKNOWN` when the required research artifacts are missing.

- **Data Lineage Fingerprint**: `/run data_lineage_fingerprint`
- **Backtest Repro Gate**: `/run backtest_repro_gate candidate_id="vol_compression_v1__short__squeeze_release" slice_ref="BEAR@4h" code_ref="HEAD" runs=3`
- **Backtest Reproducibility**: `/run backtest_reproducibility_audit backtest_id="BT_20260226_A" baseline_sha="abcd123"`
- **Factor Health**: `/run factor_health_and_drift_report factor_id="alpha_trend_v1"`
- **Strategy Sensitivity**: `/run strategy_regime_sensitivity_report strategy_id="trend_mvp_btc_1h"`

---

## 📂 SSOT Artifact Requirements

To transition a skill from `UNKNOWN` to `OK`, the following SSOT files must be present and readable in `data/state/` or `reports/research/`:

| Skill | Required SSOT File / Path |
|-------|---------------------------|
| `system_health_morning_brief` | `data/state/system_health_latest.json` |
| `incident_timeline_builder` | `data/state/system_health_latest.json` (or component files) |
| `data_freshness_watchdog_report` | `data/state/freshness_table.json` |
| `execution_quality_report_readonly` | `data/state/execution_quality_latest.json` |
| `data_lineage_fingerprint` | `data/state/daily_report_latest.json`, `data/state/freshness_table.json`, `reports/state_atomic/regime_monitor_latest.json` |
| `backtest_repro_gate` | `/daily latest_backtest_head summary` (or explicit summary path) |
| `backtest_reproducibility_audit` | `reports/research/**/*reproducibility.json` |
| `factor_health_and_drift_report` | `reports/research/factors/factor_health_<id>.json` |
| `strategy_regime_sensitivity_report` | `reports/research/sensitivity/sensitivity_<id>.json` |

---

## 🛡️ Guardrail Status

- **Core Invariant**: All skills are READ-ONLY.
- **No-Exec**: No `subprocess`, `os.system`, or `Popen` calls in `tg_cp`.
- **SSOT-Only**: Data is pulled exclusively from canonical state/research files.
