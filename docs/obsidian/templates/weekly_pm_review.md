---
date: YYYY-MM-DD
week: YYYY-WNN
ssot_ts_utc: ""
linked_prs: []   # list of "#NNN" merged this week
status: draft
---

# Weekly PM Review: {{ week }}

> Focus: Is the strategy portfolio developing meaningfully? Is governance hardening?

## 1. Sample Counts & Data Quality

| Symbol | Timeframe | Candles (IS) | Candles (OOS fresh) | Freshness Status |
|--------|-----------|-------------|---------------------|-----------------|
| BTCUSDT | 4h | | | |
| ETHUSDT | 4h | | | |

- **Max age (h):**
- **WARN symbols:**
- **Freshness SSOT status:** OK / WARN / FAIL

## 2. Output Convergence

| Strategy | Direction | Score Δ (vs last week) | OOS Sharpe | Gate |
|----------|-----------|------------------------|------------|------|
| | LONG | | | PASS/FAIL |
| | SHORT | | | PASS/FAIL |

- **New promotions this week:**
- **Demotions / retirements:**
- **Regime signal status:**

## 3. Overfit Gate Summary

| Gate | Pass | Warn | Fail | Unknown |
|------|------|------|------|---------|
| Today | | | | |
| Last week | | | | |

- **Governance policy in effect:** (e.g. `aggressive_yield_first_v1`)
- **Policy change this week?** yes / no → PR:

## 4. Governance Hardening

| Item | Status | Notes |
|------|--------|-------|
| Regime threshold calibration | OK/STALE | Last: YYYY-MM-DD |
| Coverage matrix | PASS/FAIL | |
| Core diff = 0 | ✅/❌ | |
| Data committed? | ✅ none / ❌ found | |

## 5. Incidents / Anomalies This Week
<!-- Link to incident notes if any -->
- None / See: `Incidents/YYYY-MM-DD_<slug>.md`

## 6. Decisions Made
<!-- Link to decision logs if any -->
- None / See: `Decisions/YYYY-MM-DD_<topic>.md`

## 7. Next Week Priorities

1.
2.
3.

## References

- SSOT: `data/state/daily_report_latest.json` at `{{ ssot_ts_utc }}`
- Merged PRs this week: {{ linked_prs }}
