# System Health Report (Baseline Gate Re-Run)

- Date: 2026-02-18
- Source log: `tmp/baseline_gate_2026-02-18.log`
- Scope: run baseline gate in required order with local `.venv` tooling.

## Gate Results

| # | Command | Exit | Key note |
|---|---|---:|---|
| 1 | `./.venv/bin/python -m pytest -q` | 1 | 1 test failed (`test_force_trade_with_send_hits_broker`) |
| 2 | `./.venv/bin/python scripts/exchange_smoke_test.py --debug_signing` | 1 | missing `BINANCE_API_KEY` / `BINANCE_API_SECRET` |
| 3 | `bash scripts/smoke_backtest.sh` | 0 | smoke backtest passed |
| 4 | `bash scripts/walkforward_suite.sh --quick` | 0 | windows failed internally (`tee: /dev/tty` + pipeline fail), script returns 0 |
| 5 | `./.venv/bin/python scripts/report_walkforward.py` | 0 | report generated |
| 6 | `./.venv/bin/python scripts/generate_selection_artifact.py --run_dir data/backtests/2026-02-18/20260218_162113_af67` | 0 | selection generated (HOLD) |
| 7 | `./.venv/bin/python scripts/generate_action_items.py` | 0 | action items generated |
| 8 | `./.venv/bin/python scripts/execute_paper.py --debug_signing` | 0 | HOLD, no orders |
| 9 | `./.venv/bin/python scripts/order_reconcile.py` | 0 | no orders to reconcile |
| 10 | `./.venv/bin/python -m ruff check .` | 1 | `ruff` module missing in `.venv` |

## Stop Conditions

Triggered:
- Tests not fully green.
- Exchange smoke blocked by missing secrets.
- Lint tool missing in environment.

Follow-up:
1. Fix failing test in `tests/test_execute_paper_force_trade.py`.
2. Provide testnet key/secret for signed API verification.
3. Install `ruff` in `.venv` or switch lint invocation to project-managed runner.
