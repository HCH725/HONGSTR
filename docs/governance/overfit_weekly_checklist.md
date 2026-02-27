> [!IMPORTANT] REFERENCE ONLY - Please see [Daily Report & Glossary](docs/ops/daily_report_zh.md) for current entry point.

# Weekly Overfit Checklist (Template)

Use this checklist when reviewing weekly research governance outputs.

## 1) Inputs Freshness

- [ ] `bash scripts/refresh_state.sh` completed successfully
- [ ] `data/state/system_health_latest.json` exists
- [ ] `data/state/strategy_pool_summary.json` exists
- [ ] latest research artifacts exist under `reports/research/`

## 2) Hard Gate Review

- [ ] OOS Sharpe floor respected
- [ ] OOS MDD ceiling respected
- [ ] Trades minimum respected
- [ ] PnL multiplier minimum respected
- [ ] IS/OOS Sharpe ratio overfit rule respected

## 3) Soft Gate Penalty Review

- [ ] score penalties align with policy (`research/policy/overfit_gates_aggressive.json`)
- [ ] soft penalties are reflected in ranking order
- [ ] no silent drop of weak candidates (must be WATCHLIST or DEMOTE)

## 4) Candidate Continuity

- [ ] watchlist floor active (candidate count does not go to zero)
- [ ] at least one candidate appears in weekly recommendation

## 5) Outputs

- [ ] `weekly_quant_checklist.md` generated (report-only)
- [ ] `weekly_quant_checklist.json` generated (report-only)
- [ ] recommendations include `promote/demote/watchlist`

## 6) Escalation

If outputs look inconsistent:

1. Re-run refresh and research loop in dry run
2. Validate gate config and artifact schema
3. Open docs-only PR for policy/example mismatch

