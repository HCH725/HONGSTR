# HONGSTR Brake System Inventory (v1)

> Purpose: Make all "brakes" explicit and auditable: gates, OOS/WF splits, needs_rebase, anti-churn, and SOP.

## 1) Artifact Contract (Brake-related state files)

| Artifact | Path Pattern | Producer (script/job) | Consumer (tg_cp/dashboard/cli) | Status (Found/Not Found) |
|---|---|---|---|---|
| gate.json | `data/backtests/*/*/gate.json` | `scripts/generate_gate_artifact.py` | `scripts/generate_selection_artifact.py` | Found |
| selection.json | `data/backtests/*/*/selection.json` | `scripts/generate_selection_artifact.py` | Dashboard, Paper Trader | Found |
| summary.json | `data/backtests/*/*/summary.json` | Backtest Engine | `gate_all.sh`, `generate_gate_artifact.py` | Found |
| freshness_table.json | `data/state/freshness_table.json` | `scripts/coverage_update.py` | TG Summary, Dashboard | Found |
| regime_monitor_latest.json | `data/state/regime_monitor_latest.json` | `scripts/phase4_regime_monitor.py` | Research Loop, Dashboard | Found |
| coverage_table.jsonl | `data/state/coverage_table.jsonl` | `scripts/check_data_coverage.sh` | `scripts/semantics_check.py` | Found |

## 2) OOS/WF Rules (Fixed splits)

- **Where encoded**: `scripts/phase3_walkforward.sh`
- **Exact split ranges**:
  - **FIXED**: IS: 2020-01-01 -> 2023-12-31 | OOS: 2024-01-01 -> now
  - **WF1**: IS: 2020-01-01 -> 2022-12-31 | OOS: 2023-01-01 -> 2023-12-31
  - **WF2**: IS: 2020-01-01 -> 2023-12-31 | OOS: 2024-01-01 -> 2024-12-31
  - **WF3**: IS: 2020-01-01 -> 2024-12-31 | OOS: 2025-01-01 -> now
- **How to verify**: Run `bash scripts/phase3_walkforward.sh` and inspect `run_index.tsv`.

## 3) Gates & Thresholds

- **Gate types**: OOS Sharpe Floor, OOS MDD Ceiling, Overfit Detection (IS/OOS Ratio), Trade Count Floor.
- **Thresholds**:
  - `min_oos_sharpe`: 0.5 (Base) / 0.1 - 0.3 (Regime-specific)
  - `max_oos_mdd`: -15% (Base) / -25% - -30% (Regime-specific)
  - `overfit_ratio`: 2.0 (IS Sharpe / OOS Sharpe)
  - `trade_count`: `max(30, int(window_days * 0.5))` (Adaptive)
- **Where encoded**: `research/loop/gates.py`, `scripts/generate_gate_artifact.py`.

## 4) NEEDS_REBASE / Drift Detection

- **Signal**: Semantics version mismatch.
- **Where encoded**: `scripts/semantics_check.py` compares `configs/semantics_version.json` vs `data/state/coverage_table.jsonl`.
- **SOP**: Update `coverage_table.jsonl` status to `NEEDS_REBASE`, halting downstream pipelines until backfill is re-run.

## 5) Anti-churn / Promotion Policy

- **Policy**: **NOT FOUND** as explicit script.
- **Implicit Mechanism**: `scripts/generate_selection_artifact.py` enforces `decision=HOLD` if `gate.json` status is not `PASS`. This prevents unstable strategies from promotion to selection.

## 6) SOP: What to do on WARN/FAIL

### Coverage/Freshness FAIL

- **Commands**: `bash scripts/check_data_coverage.sh`, `bash scripts/backfill_1m_from_2020.sh`
- **Logs**: `logs/coverage_check.log`

### Gate FAIL

- **Commands**: `python3 scripts/generate_gate_artifact.py --dir <run_dir> --mode FULL --symbols BTCUSDT` (to re-evaluate)
- **Logs**: `logs/gate_all_*.log`

### Regime Monitor WARN/FAIL

- **Commands**: `python3 scripts/phase4_regime_monitor.py`
- **Logs**: `data/state/regime_monitor_latest.json` (inspect `overall_reason`)
