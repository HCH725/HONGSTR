# Overfit Governance (Aggressive / Yield-first)

This policy is the research-layer governance contract for high-yield candidate ranking while still enforcing minimum safety floors.

- SSOT policy file: `research/policy/overfit_gates_aggressive.json`
- Execution stance: `report_only`
- Core safety: no `src/hongstr/**` mutation, no trading behavior change

## Hard Gates (must pass all)

1. `oos_sharpe >= 0.75`
2. `oos_mdd >= -0.25`
3. `is_sharpe / oos_sharpe <= 2.2`

Any hard-gate failure is a `demote` recommendation.

## Soft Ranking (yield-first)

Candidates that pass hard gates are ranked by:

`score = (oos_sharpe*100) + (oos_return*100) - drawdown_penalty - overfit_penalty`

Bands:

- `score >= 82` -> `promote`
- `60 <= score < 82` -> `watchlist`
- `< 60` -> `demote`

## Weekly Deliverables

- Runtime report (not committed): `reports/governance/overfit_weekly_<week_id>.md`
- Specialist output schema:
  - top-level: `schema_version, week_id, generated_at, report_only, actions, summary, recommendations`
  - `recommendations[].recommendation` in `{promote, demote, watchlist}`

## Rollback

If this governance policy produces undesired behavior:

1. Revert the merge commit:
   - `git revert <merge_commit_sha>`
2. Re-run preflight and regenerate weekly report in report-only mode.
