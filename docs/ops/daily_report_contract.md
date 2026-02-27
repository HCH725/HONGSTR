# Daily Report Contract (SSOT)

> REFERENCE ONLY
>
> 主入口請看 `docs/ops/daily_report_single_entry.md` 與 Telegram `/daily`。

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

- **SystemHealth**: `ssot_status`, `ssot_components`, `ssot_components.regime_signal.threshold_*`, `ssot_components.regime_signal.calibration_status` (`OK|WARN|STALE|UNKNOWN`), `ssot_components.regime_signal.last_calibrated_utc`
- **DataFreshness**: `freshness_summary.counts`, `freshness_summary.profile_totals`, `freshness_summary.top_offenders`
- **Backtest**: `latest_backtest_head.artifacts`, `latest_backtest_head.metrics`, `latest_backtest_head.gate`, `latest_backtest_head.metrics_status`, `latest_backtest_head.regime_window_utc`, `latest_backtest_head.slice_rationale`, `latest_backtest_head.fallback_reason`
- **StrategyPool + Leaderboard**: `strategy_pool.summary`, `strategy_pool.leaderboard_top[*].direction`, `strategy_pool.direction_coverage.short_coverage`
- **StrategyPool + Leaderboard (B1 extension, optional)**: `research_leaderboard.entries[*].regime_slice` (`ALL|BULL|BEAR|SIDEWAYS`) and optional `regime_window_start_utc`/`regime_window_end_utc` for report-only regime timeline wiring.
- **Slice Comparison Spec (stability-first)**:
  - `slice_comparison_key = strategy_id|direction|variant|regime_slice`
  - Any comparison of the same `strategy_id` across different slices must include `regime_slice` (or `slice_comparison_key`) to avoid sample contamination.
- **Governance(Overfit)**: `governance.overfit_gates_policy.name`, `governance.today_gate_summary`
- **Guardrails summary**: `guardrails.checks`

## /daily Rendering Rules

- Default output must be deterministic fallback template.
- LLM polishing is optional and must preserve numeric values from SSOT JSON.
- Missing fields must render as `資料不足/UNKNOWN`, never coercing to `0.00`.
- Slice fallback must render explicit reason from `fallback_reason` (or `slice_rationale`) when `regime_slice=ALL` due to degrade path.
- Acronyms must include zh-TW explanation at least once in the message:
  - `SSOT`, `DD`, `MDD`, `Sharpe`, `Trades`, `OOS`, `IS`, `WF`, `L1`, `L2`, `L3`, `TP`, `SL`, `DCA`
- Fixed section order (6): `SystemHealth -> DataFreshness -> Backtest -> StrategyPool+Leaderboard -> Governance(Overfit) -> Guardrails`
- Fixed per-section shape (3 lines): `狀態`, `白話`, `下一步`

## Example /daily Output (shape)

```text
📘 每日報告（Single Entry /daily）
DAILY_REPORT_STATUS: OK|WARN
GeneratedUTC: 2026-02-27T03:46:59Z
縮寫: SSOT（...）、DD（...）、MDD（...）、Sharpe（...）、Trades（...）、OOS（...）、IS（...）、WF（...）、L1（...）、L2（...）、L3（...）、TP（...）、SL（...）、DCA（...）

1) SystemHealth
狀態: ...
白話: ...
下一步: ...

2) DataFreshness
狀態: ...
白話: ...
下一步: ...

3) Backtest
狀態: ...
白話: ...
下一步: ...

4) StrategyPool+Leaderboard
狀態: ...
白話: ...
下一步: ...

5) Governance(Overfit)
狀態: ...
白話: ...
下一步: ...

6) Guardrails
狀態: ...
白話: ...
下一步: ...
需要時參考: docs/inventory.md | docs/ops/telegram_operator_manual.md
RefreshHint: bash scripts/refresh_state.sh
```
