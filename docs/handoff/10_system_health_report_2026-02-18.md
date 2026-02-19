# System Health Report (Baseline, No Code Change)

- Date: 2026-02-18
- Scope: Executed baseline gate exactly in requested order, without code changes.
- Safety mode: no `--send` used.
- Result: **STOP CONDITION TRIGGERED** (multiple gate failures).

## 1) Gate Checklist Results

| # | Command | Exit | Key output (top 3 lines / most critical) |
|---|---|---:|---|
| 1 | `pytest -q` | 127 | `zsh:1: command not found: pytest` |
| 2 | `python3 scripts/exchange_smoke_test.py --debug_signing` | 1 | `ERROR: BINANCE_API_KEY and BINANCE_API_SECRET must be set.` |
| 3 | `bash scripts/smoke_backtest.sh` | 0 | `--- Backtest Finished ---` / `Results saved to: tmp/backtests_smoke/2026-02-18/081301` / `SUCCESS: Backtest Smoke Passed.` |
| 4 | `bash scripts/walkforward_suite.sh --quick` | 0 | `Quick Mode: Running first 2 windows, Symbol: BTCUSDT` / `tee: /dev/tty: Operation not permitted` / `Error: Backtest pipeline failed for BULL_2021_H1 (Exit 1)` |
| 5 | `python3 scripts/report_walkforward.py` | 0 | `Generated reports in reports` |
| 6 | `python3 scripts/generate_selection_artifact.py` | 2 | `error: the following arguments are required: --run_dir` |
| 7 | `python3 scripts/generate_action_items.py` | 0 | `Generated reports/action_items_latest.md and reports/action_items_latest.json` |
| 8 | `python3 scripts/execute_paper.py --debug_signing` | 0 | `Using selection from: data/backtests/2026-02-17/20260218_001719_95ef/selection.json` / `Decision is HOLD. No orders generated.` / `Reports written to reports/orders_latest.json and .md` |
| 9 | `python3 scripts/order_reconcile.py` | 0 | `No orders to reconcile.` |
| 10 | `ruff check .` | 127 | `zsh:1: command not found: ruff` |

## 2) Artifact Evidence

### A. Backtest per-run isolation artifacts

- Run dir: `tmp/backtests_smoke/2026-02-18/081301`
- Exists:
  - `tmp/backtests_smoke/2026-02-18/081301/trades.jsonl`
  - `tmp/backtests_smoke/2026-02-18/081301/equity_curve.jsonl`
  - `tmp/backtests_smoke/2026-02-18/081301/summary.json`
- `summary.json` keys:
  - `['avg_trade_return','cagr','config','end_equity','end_ts','exposure_time','max_drawdown','per_symbol','run_id','sharpe','start_equity','start_ts','timestamp','total_return','trades_count','win_rate']`
- `trades.jsonl` first-record keys:
  - `['entry_price','exit_price','fees','pnl','pnl_pct','qty','reason','side','signal_id','symbol','trade_id','ts_entry','ts_exit']`
- `equity_curve.jsonl` first-record keys:
  - `['cash','equity','position_notional','ts']`

### B. Walkforward / Action / Orders artifacts

- `reports/walkforward_latest.json` exists, keys:
  - `['generated_at','stability','windows','windows_completed','windows_total']`
- `reports/walkforward_latest.md` exists.
- `reports/action_items_latest.json` exists, keys:
  - `['decision','failing_windows','generated_at','overall_gate','source','top_actions']`
- `reports/action_items_latest.md` exists.
- `reports/orders_latest.json` exists, keys:
  - `['decision','dry_run','forced','orders','regime','source_selection','timestamp']`
- `reports/orders_latest.md` exists.

### C. Selection artifact contract (repo current state)

- Baseline command `generate_selection_artifact.py` failed because `--run_dir` is required.
- Existing selection artifacts found at:
  - `data/artifacts/selection.json` (keys: `['items','portfolio_id','timestamp']`)
  - `data/backtests/*/*/selection.json` (sample keys: `['candidates','decision','gate','generated_at','inputs','reasons','regime','regime_tf','run_dir','schema_version','selected']`)
- This indicates **multiple selection schemas/locations coexist**.

## 3) Quick Mode Window Count Check

- `configs/windows.json` total windows: `5`
- quick expected windows: `2` (first two: `BULL_2021_H1`, `BEAR_2022`)
- Actual quick run logs: both windows failed in pipeline.
- But generated `reports/walkforward_latest.json` shows:
  - `windows_total = 5`
  - `windows_completed = 5`
- Interpretation: report likely reused historical completed runs instead of reflecting current quick execution outcome.

## 4) Stop Conditions Status

Triggered:
- Gate checklist failures (`pytest`, `exchange_smoke_test`, `generate_selection_artifact`, `ruff`).
- Verification inconsistency (quick run failed but latest report still 5/5 completed).

Not yet triggered in this baseline run:
- No schema change introduced (no code edits).
- No signing refactor attempted.

## 5) Immediate Stabilization Targets (scripts/tests only)

1. Fix walkforward quick verification path so current run status is represented as `PENDING` when not completed.
2. Fix baseline selection generation invocation contract (`--run_dir` handling via suite/verify pipeline).
3. Normalize tooling entry points (`pytest`, `ruff`) to deterministic env invocation (`./.venv/bin/...` or script wrapper).

## Known Limitations

- `pip install -e ".[dev]"` can fail in offline environments because build backend dependency resolution (for example `hatchling`) cannot reach package index. This is an environment limitation and is not treated as a gate logic bug.
- `aiofiles` may be missing in minimal environments. Tests requiring it are guarded by `pytest.importorskip("aiofiles")`, so they are optional and should be reported as `SKIP` rather than failures.
