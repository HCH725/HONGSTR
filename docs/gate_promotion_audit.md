# HONGSTR Gate/Promotion Audit (R5-A)

> REFERENCE ONLY


## 1) What we mean by "Gate" and "Promotion"

- **Gate**: Quantitative thresholds that block or warn based on performance metrics (Sharpe, MDD, Trade counts, Exposure). It serves as a quality filter for backtest runs.
- **Promotion**: The process of selecting a specific strategy/parameter set for "production" visibility or live execution decisions. Managed via selection artifacts.

## 2) Evidence search (files + keywords)

- **Keywords**: `gate.json`, `selection.json`, `min_sharpe`, `max_mdd`, `ResearchGate`.
- **Key Files**:
  - `scripts/generate_gate_artifact.py`: Produces `gate.json`.
  - `scripts/generate_selection_artifact.py`: Produces `selection.json`.
  - `research/loop/gates.py`: Defines experiment evaluation logic (`ResearchGate`).
  - `scripts/gate_summary.py`: CLI viewer/validator for gate status.
  - `scripts/daily_backtest.sh`: Orchestrator calling the generators.

## 3) Findings (FOUND/IMPLEMENTED)

### Gate artifacts

- **gate.json**:
  - **Producer**: `scripts/generate_gate_artifact.py`
  - **Consumer**: `scripts/gate_summary.py`, `scripts/generate_selection_artifact.py`.
  - **Status**: **FOUND & ACTIVE**. Implements regime-aware filtering (BULL/BEAR/NEUTRAL).

### Promotion/Selection artifacts

- **selection.json**:
  - **Producer**: `scripts/generate_selection_artifact.py`
  - **Consumer**: `scripts/report_strategy_research.py`, `scripts/walkforward_suite.sh`.
  - **Status**: **FOUND & ACTIVE**. Uses gate status to decide `TRADE` vs `HOLD`.
- **hong_selected.json**:
  - **Producer**: Manual or `scripts/smoke_c14_paper.sh`.
  - **Status**: **LEGACY/STUB**. Primarily used for demo/smoke tests.

## 4) Exact thresholds (FOUND)

### Production Gates (Adaptive)

Stored in `scripts/generate_gate_artifact.py` (Default) or `configs/gate_thresholds.json`:

- **Global Constraints**:
  - `min_trades_portfolio_min`: 30 trades.
  - `min_trades_per_day`: 0.5 trades/day (window relative).
- **Regime-Specific**:
  - **BULL**: min_sharpe: 0.3, max_mdd: -0.25
  - **BEAR**: min_sharpe: 0.1, max_mdd: -0.30
  - **NEUTRAL**: min_sharpe: 0.2, max_mdd: -0.25

### Research Gates (OOS/WF)

Stored in `research/loop/gates.py`:

- `min_oos_sharpe`: 0.5
- `max_oos_mdd`: -0.15 (-15%)
- `overfit_ratio`: 2.0 (IS_Sharpe / OOS_Sharpe)

## 5) SOP linkage

- **If Gate FAIL**:
  - `scripts/daily_backtest.sh` continues (artifacts are kept) but `selection.json` will set `decision: HOLD`.
  - Telegram notifications (via `tg_cp`) will surface the FAIL/WARN status.
- **If Promotion ambiguous**:
  - Fallback is `HOLD`. No trade selection is promoted if `gate.json` or `optimizer_regime.json` is missing.

## 6) Recommendation (next PR scope)

- **Consistency**: Align `scripts/gate_summary.py` legacy hardcoded fallbacks with `scripts/generate_gate_artifact.py` defaults to avoid confusing diffs when `gate.json` is missing.
- **Visibility**: Add the `overfit_ratio` from `ResearchGate` into the standard `gate.json` artifact for unified visibility in the Dashboard.
- **Strictness**: Consider a `--strict` flag in `daily_backtest.sh` to halt downstream ETL if Gate fails (currently it is a soft-fail).
