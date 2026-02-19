# Phase 3-1: Quick Suite Data Backfill

## Goal
Make `bash scripts/walkforward_suite.sh --quick --symbols BTCUSDT` runnable in local/offline baseline setups by auto-preparing the local 1m source data expected by backtest scripts.

## What Changed
- Added `scripts/ensure_quick_data.sh`.
- Wired `scripts/walkforward_suite.sh` (quick mode) to call `ensure_quick_data.sh` before running windows.

## Data Contract
- Backtest source path: `data/derived/<SYMBOL>/1m/klines.jsonl`
- Backfill scope: first 2 windows in `configs/windows.json` (quick mode scope)
- Output diagnostics: `reports/quick_data_check.md`

## Behavior
1. Parse quick windows from config.
2. Compute required UTC range from window `start/end`.
3. Ensure 1-minute bars exist for that range.
4. If missing, generate deterministic synthetic 1m bars (non-network fallback) and merge into `klines.jsonl`.
5. Write a machine-auditable summary to `reports/quick_data_check.md`.

## Notes
- This does not modify core strategy/engine/execution code.
- Latest pointer policy is unchanged.
- Use `--skip_ensure_data` on walkforward suite if you want to bypass auto-backfill.
