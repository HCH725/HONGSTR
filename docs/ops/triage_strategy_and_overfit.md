# Ops: Strategy Triage & Overfit Governance

Guide for Quant Specialists for periodic strategy auditing and overfitting governance.

## 1. Governance Gates (G0 - G6)

Strategies must progress through these gates before they can influence the `strategy_pool`.

- **G0 (Sandbox)**: Free-form research; no compliance requirement.
- **G1 (Verificable)**: Baseline SHA matches; reproducibility PASS.
- **G2 (OOS Split)**: 70/30 IS/OOS split validated; zero leakage.
- **G3 (Regime Robust)**: PASS across multiple market regimes (Volatile/Trending/Range).
- **G4 (Cost Aware)**: Slippage and fee modeling (L1-L3) applied.
- **G5 (Peer Audit)**: Qualitative review by Steward/PM.
- **G6 (Production Candidate)**: Promoted to `strategy_pool` in `report_only` mode.

## 2. Overfit Weekly Checklist

Weekly routine for the Quant Specialist:

1. **Verify `gate.json`**: Ensure all candidates in the `strategy_pool` have recent G1-G3 status.
2. **Check OOS Decay**: Compare current OOS Sharpe vs. historical IS Sharpe. Promotion halted if decay > 50%.
3. **Audit Leakage**: Run `/run signal_leakage_and_lookahead_audit` on any new G6 candidate.
4. **Inspect Leaders**: Review `leaderboard.json` to identify high-diversification candidates (e.g., Short-only or DCA).

## 3. "Single Ruler" Summary Philosophy

> "We prioritize **Yield** but mandate **Auditability**. A strategy may be aggressive, but its overfitting risk must be quantified and logged."

---
Safety Statement: core diff=0 | report_only | no-exec
