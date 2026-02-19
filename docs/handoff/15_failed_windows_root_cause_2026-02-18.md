# Failed Windows Root Cause (2026-02-18)

Source report: `reports/walkforward/20260218_145025_3ba186a/walkforward.json`

| window | regime | gate_status | fail_reasons(list) | trades_portfolio | trades_per_symbol | sharpe | mdd | exposure | required_trades | thresholds_used |
|---|---|---|---|---:|---|---:|---:|---:|---:|---|
| BULL_2021_H1 | BULL | ERROR (`pipeline_exit_1`) | `["MISSING_METRIC", "LOW_TRADES"]` | N/A | N/A | N/A | N/A | N/A | 30 (config baseline) | `configs/gate_thresholds.json`: mode=`SHORT`, regime=`BULL`, `min_sharpe=0.0`, `max_mdd=-0.15`, plus global `min_trades_per_day=0.8`, `min_trades_portfolio_min=30` |
| BEAR_2022 | BEAR | ERROR (`pipeline_exit_1`) | `["MISSING_METRIC", "LOW_TRADES"]` | N/A | N/A | N/A | N/A | N/A | 30 (config baseline) | `configs/gate_thresholds.json`: mode=`SHORT`, regime=`BEAR`, `min_sharpe=0.0`, `max_mdd=-0.15`, plus global `min_trades_per_day=0.8`, `min_trades_portfolio_min=30` |

## Notes

- Root cause is upstream of gate scoring: `run_and_verify.sh` exits before `summary.json` is produced because local data does not cover 2021/2022 windows.
- Because run artifacts are missing, gate metrics are unavailable (`MISSING_METRIC`) and windows are marked `ERROR`.
- This is not a signing/execution/core-engine issue.
