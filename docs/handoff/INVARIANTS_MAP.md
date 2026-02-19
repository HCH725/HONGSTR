# INVARIANTS MAP (Protected Contracts)

- Date: 2026-02-18
- Purpose: define protected behaviors and file ownership boundaries that must not be changed without explicit justification and verification.

## 1) Backtest Semantics Invariant

Protected behavior:
- Signal at bar `T` close, fill at bar `T+1` open (`next_open`).
- Do not open new position at last bar when `T+1` fill is impossible.
- Keep deterministic outputs with `timestamp_convention = bar_start_utc`.

Protected files:
- `src/hongstr/backtest/engine.py`
- `scripts/run_backtest.py`
- `tests/test_backtest.py`
- `tests/test_backtest_deterministic.py`

Validation focus:
- `./.venv/bin/python -m pytest -q tests/test_backtest.py tests/test_backtest_deterministic.py`

## 2) Binance Signing / Transport Invariant

Protected behavior:
- Build pre-sign query string from sorted params.
- Sign exactly once from the same query string.
- Send signed calls via full URL only; do not pass `params`, `data`, or `json` for signed transport.

Protected files:
- `src/hongstr/execution/binance_utils.py`
- `src/hongstr/execution/binance_testnet.py`
- `scripts/exchange_smoke_test.py`
- `scripts/execute_paper.py`
- `tests/test_binance_utils.py`
- `tests/test_exchange_smoke_test.py`

Validation focus:
- `./.venv/bin/python -m pytest -q tests/test_binance_utils.py tests/test_exchange_smoke_test.py`

## 3) Execution Contract Invariant

Protected behavior:
- Preserve `OrderRequest` / `OrderResult` model schema compatibility.
- Preserve dry-run vs send behavior boundaries.
- Preserve reconcile idempotency.

Protected files:
- `src/hongstr/execution/models.py`
- `src/hongstr/execution/broker.py`
- `src/hongstr/execution/executor.py`
- `src/hongstr/execution/paper.py`
- `scripts/order_reconcile.py`
- `tests/test_execution.py`
- `tests/test_reconcile.py`

Validation focus:
- `./.venv/bin/python -m pytest -q tests/test_execution.py tests/test_reconcile.py`

## 4) Artifact Contract Invariant

Protected behavior:
- Keep required report/artifact files and top-level schema keys stable.
- Keep walkforward/action/orders latest report contracts intact.

Protected files:
- `scripts/report_walkforward.py`
- `scripts/generate_action_items.py`
- `scripts/generate_selection_artifact.py`
- `scripts/generate_gate_artifact.py`
- `scripts/gate_summary.py`

Validation focus:
- `./.venv/bin/python -m pytest -q tests/test_walkforward_report.py tests/test_action_items.py tests/test_gate_artifact.py tests/test_gate_summary.py`

## 5) Baseline Gate (Mandatory Order)

Run in this exact order:
1. `./.venv/bin/python -m pytest -q`
2. `./.venv/bin/python scripts/exchange_smoke_test.py --debug_signing`
3. `bash scripts/smoke_backtest.sh`
4. `bash scripts/walkforward_suite.sh --quick`
5. `./.venv/bin/python scripts/report_walkforward.py`
6. `./.venv/bin/python scripts/generate_selection_artifact.py --run_dir <latest_run_dir>`
7. `./.venv/bin/python scripts/generate_action_items.py`
8. `./.venv/bin/python scripts/execute_paper.py --debug_signing`
9. `./.venv/bin/python scripts/order_reconcile.py`
10. `./.venv/bin/python -m ruff check .`

## 6) Protected Files Auto-Check

Single source of truth:
- `configs/protected_files.txt`

Checker:
- `scripts/check_protected_files.py`

Hook:
- `.githooks/pre-commit` (installed via `scripts/install_git_hooks.sh`)

Behavior:
- If staged changes include protected files, commit is blocked by default.
- To override intentionally: `ALLOW_PROTECTED_TOUCH=1 git commit ...`

