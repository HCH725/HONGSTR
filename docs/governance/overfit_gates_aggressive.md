# Overfit Governance (Aggressive, Yield-First)

This policy is the research-loop governance standard for report-only evaluation.

- Policy file: `research/policy/overfit_gates_aggressive.json`
- Mode: `report_only`
- Scope: research artifacts only (no trading behavior change)

## Hard Gates

Candidates fail hard gate if any condition is violated:

- OOS Sharpe below floor
- OOS MDD worse than ceiling
- Trades count below minimum
- PnL multiplier below minimum
- IS/OOS Sharpe ratio above overfit ratio

## Soft Gates (Penalty Tier)

Soft gates do not remove a candidate. They lower ranking score via penalties:

- OOS Sharpe below target
- OOS MDD worse than target
- Trades shortfall
- PnL shortfall

## Watchlist Floor (Anti Lock-Dead)

To avoid `candidate_count = 0`, governance enforces a watchlist floor:

- At least `watchlist.min_candidates` candidates remain in WATCHLIST when no hard-pass candidate exists.
- This keeps research cadence alive while still penalizing weak candidates.

## Weekly Quant Checklist

Weekly artifacts are generated under:

- `reports/research/governance/<ISO_YEAR>_W<ISO_WEEK>/weekly_quant_checklist.md`
- `reports/research/governance/<ISO_YEAR>_W<ISO_WEEK>/weekly_quant_checklist.json`

They include:

- SSOT health snapshot references
- Top candidates and gate outcomes
- Promote/Demote/Watchlist recommendation (report-only)

## Rollback

After merge:

```bash
git revert <merge_commit_sha>
```
