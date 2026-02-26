# Audit: Technical Gaps in Strategy Pool (Short / Multi-Strategy / DCA)

**Date**: 2026-02-27  
**Audit Scope**: Coverage of `data/state/strategy_pool.json` vs. Research Infrastructure Capability.

## Executive Summary

| Metrics | Value | Note |
| --- | --- | --- |
| **Total Candidates in Pool** | 1 | `trend_mvp_btc_1h` |
| **Long-Only Coverage** | 100% | High concentration risk |
| **Short Strategy Presence** | 0% | Infrastructure supports, but none promoted |
| **DCA / Scalping Presence** | 0% | Architectural gap |

## GAP-1: Short-Side Neglect

- **Observation**: While `src/hongstr/execution/executor.py` and `signal/types.py` fully support `SHORT` directions, the current strategy pool is 100% Long-only.
- **Risk**: Portfolio is unable to profit or hedge during structural bear regimes (Regime Signal FAIL).
- **Existing Research**: Candidates like `rsi_divergence` and `vwap_supertrend` already have shorting logic in `src/hongstr/signal/strategies/` but lack a G6 Promotion Pipeline.

## GAP-2: Multi-Strategy Diversity

- **Observation**: The pool contains only a single EMA-based trend follower.
- **Risk**: Strategy-specific overfitting to the current high-volatility regime.
- **Missing**: Mean-reversion or high-frequency (1m) volatility capture strategies.

## GAP-3: DCA / Martingale / Grid Absence

- **Observation**: No strategies currently implement DCA (Dollar Cost Averaging) or grid-based entry/exit logic (DCA-1).
- **Constraint**: HONGSTR core (`src/hongstr`) is currently biased towards single-entry/single-exit (discrete) signal processing.

## Recommendations (Phase 2)

1. Promote at least one **Short-enabled** candidate (VWAP-Supertrend) to G3 gate.
2. Formulate a **DCA-1 Specification** that fits the `report_only` audit profile without violating core immutability.

---
*Red Line Policy: core diff=0 | report_only | tg_cp no-exec | data/**gitignored*
