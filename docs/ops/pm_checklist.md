# PM Lifecycle Checklist

This checklist is for the HONGSTR Portfolio Manager (PM) to ensure system health and strategy quality.

## Daily Audit (3 min)

### 1. System Health (SSOT)

- [ ] **Check `system_health_latest.json`**
  - Path: `data/state/system_health_latest.json`
  - Ensure `ssot_status == "OK"`.
  - **Clarification**: `ssot_status` tracks infrastructure integrity. If `regime_signal` is `FAIL`, it is a **trade-risk alert**, not a system failure.

- [ ] **Data Freshness**
  - Path: `data/state/freshness_table.json`
  - Ensure kline latency is within acceptable bounds (Check metadata).

- [ ] **Brake Status**
  - Path: `reports/state_atomic/brake_health_latest.json`
  - Verify all safety brakes are engaged and green.

### 2. Strategy Pool Monitoring

- [ ] **Review pool summary**
  - Path: `data/state/strategy_pool_summary.json`
  - Verify no unexpected strategy demotions.

## Weekly Audit (45 min)

### 1. Alpha Integrity

- [ ] **Inspect Leaderboard**
  - Path: `data/state/_research/leaderboard.json`
  - identify top 3 candidate strategies for deep dive.

- [ ] **Verify Backtest Artifacts**
  - Paths: `data/backtests/**/summary.json`, `selection.json`, `gate.json`.
  - Ensure `gate.json` shows PASS for high-priority candidates (G0-G6).

### 2. Model Drift & Coverage

- [ ] **Regime Sensitivity**
  - Review `docs/audits/current_gaps_short_multi_strategy_dca.md` (if applicable).
  - Check if any new candidate fills known gaps (Shorts/DCA/Grid).

---
Safety Level: High (Read-only / Audit)
