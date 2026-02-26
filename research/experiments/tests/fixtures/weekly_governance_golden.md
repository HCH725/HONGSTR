# Weekly Overfit Governance Report (2026-W09)

- GeneratedAt: `2026-02-27T00:00:00+00:00`
- Mode: `report_only` (`actions=[]`)
- HardGates: `{"min_oos_sharpe": 0.75, "max_drawdown": -0.25, "max_overfit_ratio": 2.2}`

## Summary
- Total Candidates: `4`
- Promote: `2`
- Watchlist: `1`
- Demote: `1`

## Recommendations
| strategy_id | direction | variant | soft_score | recommendation | hard_gate_pass |
| --- | --- | --- | ---: | --- | --- |
| trend_mvp_btc_1h | LONG | base | 121.72 | promote | PASS |
| trend_supertrend_eth_1h_short | SHORT | v_short | 85.35 | promote | PASS |
| vol_keltner_breakout_eth_1h | LONG | base | 78.31 | watchlist | PASS |
| mr_bbands_eth_1h | LONG | base | -7.57 | demote | FAIL |

## Policy
- Hard gate failures are never auto-promoted.
- Soft score ranking is used for yield-first ordering among hard-gate pass candidates.
- Suggestions only (`promote/demote/watchlist`); no automatic system mutation.
