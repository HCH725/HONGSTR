# HONGSTR Brake System Inventory (v1.1)

> Purpose: Make all "brakes" explicit and auditable: gates, OOS/WF splits, needs_rebase, anti-churn, and SOP.

## 1) Artifact Contract (Brake-related state files)

| Artifact | Path Pattern | Producer | Consumer | Status |
|---|---|---|---|---|
| gate.json | `data/backtests/*/*/gate.json` | `scripts/generate_gate_artifact.py` | Selection | Found |
| selection.json | `data/backtests/*/*/selection.json` | `scripts/generate_selection_artifact.py` | Dashboard/Paper | Found |
| summary.json | `data/backtests/*/*/summary.json` | Backtest Engine | Gate Scripts | Found |
| freshness_table.json | `data/state/freshness_table.json` | `scripts/coverage_update.py` | Dashboard | Found |
| regime_monitor_latest.json | `data/state/regime_monitor_latest.json` | `scripts/phase4_regime_monitor.py` | Loop | Found |

## 2) OOS/WF Rules (Exact Split)

Formal backtest/research split ranges defined in `scripts/phase3_walkforward.sh`:

- **FIXED**: IS: `2020-01-01` -> `2023-12-31` | OOS: `2024-01-01` -> `now`
- **WF1**: IS: `2020-01-01` -> `2022-12-31` | OOS: `2023-01-01` -> `2023-12-31`
- **WF2**: IS: `2020-01-01` -> `2023-12-31` | OOS: `2024-01-01` -> `2024-12-31`
- **WF3**: IS: `2020-01-01` -> `2024-12-31` | OOS: `2025-01-01` -> `now`

## 3) SOP (One-click)

### 1. Coverage/Freshness FAIL

**Signal**: Dashboard/TG alert shows data gaps or stale timestamp.

- **Commands**:

  ```bash
  # 1. Check current coverage
  bash scripts/check_data_coverage.sh
  # 2. Trigger daily ETL (if missing today)
  bash scripts/daily_etl.sh
  # 3. Backfill from source if gaps persist
  bash scripts/backfill_1m_from_2020.sh
  ```

- **Logs**: `logs/check_data_coverage.log`
- **Expected**: "Coverage PASS" or no missing intervals in report.

### 2. Gate FAIL

**Signal**: `gate.json` shows `overall: FAIL`.

- **Commands**:

  ```bash
  # Re-evaluate gate for a specific run
  python3 scripts/generate_gate_artifact.py --dir <run_dir> --mode FULL --symbols BTCUSDT
  # Re-generate selection (respecting gate)
  python3 scripts/generate_selection_artifact.py --run_dir <run_dir>
  ```

- **Logs**: `logs/gate_all_*.log` (Generated on suite run)
- **Expected**: `gate.json` updated with latest thresholds and pass/fail reason.

### 3. Regime Monitor WARN/FAIL

**Signal**: `regime_monitor_latest.json` shows drift or anomaly.

- **Commands**:

  ```bash
  # Force update regime state
  python3 scripts/phase4_regime_monitor.py
  ```

- **State File**: `data/state/regime_monitor_latest.json`
- **Logs**: **NOT FOUND** (Search paths: `logs/`, `data/state/_research/`. Logic is direct state write.)
- **Expected**: `overall` status in JSON returns to `OK`.

## 4) Needs Rebase (Semantics Drift)

**Where encoded**: `scripts/semantics_check.py`

- **SOP**: If coverage table status is `NEEDS_REBASE`, backfill must be re-run with current `semantics_version.json`.
