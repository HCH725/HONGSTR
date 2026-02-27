# Daily Report Contract (SSOT)

## Canonical File

- Path: `data/state/daily_report_latest.json`
- Producer: `scripts/state_snapshots.py` (canonical writer boundary)
- Consumers: tg_cp `/daily` (single command, no alias), dashboard daily reporting surfaces

## Schema (v1)

Top-level keys are fixed and ordered:

1. `schema`
2. `generated_utc`
3. `refresh_hint`
4. `ssot_status`
5. `ssot_components`
6. `freshness_summary`
7. `latest_backtest_head`
8. `strategy_pool`
9. `research_leaderboard`
10. `governance`
11. `guardrails`
12. `sources`

`schema.field_labels_zh_en` provides English -> zh-TW display mapping for major fields.

## Required Sections

- **SystemHealth**: `ssot_status`, `ssot_components`
- **Freshness profiles**: `freshness_summary.counts`, `freshness_summary.profile_totals`, `freshness_summary.top_offenders`
- **Latest Backtest**: `latest_backtest_head.artifacts`, `latest_backtest_head.metrics`, `latest_backtest_head.gate`, `latest_backtest_head.metrics_status`
- **StrategyPool + Leaderboard**: `strategy_pool.summary`, `strategy_pool.leaderboard_top[*].direction`, `metrics_status`
- **Governance**: `governance.overfit_gates_policy.name`, `governance.today_gate_summary`
- **Guardrails summary**: `guardrails.checks`

## /daily Rendering Rules

- Default output must be deterministic fallback template.
- LLM polishing is optional and must preserve numeric values from SSOT JSON.
- Missing fields must render as `資料不足/UNKNOWN`, never coercing to `0.00`.
- Acronyms must include zh-TW explanation at least once in the message:
  - `SSOT`, `DD`, `Sharpe`, `Trades`, `OOS/IS`, `L1/L2/L3`

## Example /daily Output (shape)

```text
📘 每日報告（Deterministic SSOT）
DAILY_REPORT_STATUS: OK|WARN
GeneratedUTC: 2026-02-27T03:46:59Z
縮寫說明: SSOT（單一真實來源）, DD（回撤）, Sharpe（風險調整後報酬）, Trades（交易筆數）, OOS/IS（樣本外/樣本內）, L1/L2/L3（低/中/高優先級風險分層）

1) SystemHealth（系統健康）
...
2) Freshness Profiles（新鮮度分檔）
...
3) Latest Backtest（最新回測）
...
4) StrategyPool + Leaderboard（策略池與排行榜）
...
5) Governance（研究治理）
...
6) Action Items（行動項）
...
參考連結（需要時才點）: docs/inventory.md | docs/ops/telegram_operator_manual.md
RefreshHint: bash scripts/refresh_state.sh
```
