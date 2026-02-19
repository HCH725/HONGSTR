# Invariants Map (Protected Contracts)

- Date: 2026-02-18
- Scope: map protected behavior to concrete files and contracts.

## A) Backtest Semantics Invariant (`next_open`, no lookahead, deterministic)

Protected behavior:
- Signal at bar `T` close, execute at bar `T+1` open.
- Last bar cannot open a new position requiring next bar fill.
- Output config must keep `fill_mode = next_open` and `timestamp_convention = bar_start_utc`.

Primary files:
- `src/hongstr/backtest/engine.py`
  - `run()` executes `pending_order` before new signal calculation.
  - `_process_signal()` queues pending order.
  - report config hard-codes `fill_mode: next_open`, `timestamp_convention: bar_start_utc`.
- `scripts/run_backtest.py`
  - summary config writes `fill_mode: next_open`, `timestamp_convention: bar_start_utc`.
- Tests:
  - `tests/test_backtest_runner.py`
  - `tests/test_backtest_deterministic.py`

Do-not-break surface:
- order of operations in engine loop.
- summary/config keys consumed by downstream scripts/dashboard.

## B) Binance Signing Invariant (deterministic QS + URL-only signed transport)

Protected behavior:
- Sort params, then `urlencode(..., doseq=True)` exactly once for pre-sign string.
- Signature must be appended to same pre-sign QS.
- Signed request must be sent with `url=<full_signed_url>, params=None, data=None, json=None`.

Primary files:
- `src/hongstr/execution/binance_utils.py`
  - `sorted(p.items())` + `urllib.parse.urlencode(..., doseq=True)`.
  - returns final signed URL + headers.
- `src/hongstr/execution/binance_testnet.py`
  - `_request()` uses URL-only transport and prints deep debug when enabled.
- `scripts/exchange_smoke_test.py`
  - exercises GET signed request and optional POST order signed flow.
- `scripts/execute_paper.py`
  - runtime path for broker + debug signing.

Do-not-break surface:
- central signing function ownership.
- avoid duplicate/secondary encoding in callsites.

## C) Artifacts Contract Invariant

Required artifacts and current producers:
- Backtest per-run:
  - `trades.jsonl`, `equity_curve.jsonl`, `summary.json`
  - Producer: `scripts/run_backtest.py`
- Walkforward latest:
  - `reports/walkforward_latest.json`, `reports/walkforward_latest.md`
  - Producer: `scripts/report_walkforward.py`
- Action items latest:
  - `reports/action_items_latest.json`, `reports/action_items_latest.md`
  - Producer: `scripts/generate_action_items.py`
- Selection:
  - `selection.json` under run dirs and `data/artifacts/selection.json` (coexisting contract)
  - Producer: `scripts/generate_selection_artifact.py` (+ legacy/other producers)

Risk note:
- Selection currently has mixed schema variants (run-level vs `data/artifacts`).
- Dashboard/report readers must follow actual produced schema per path.

## D) Time Convention Invariant

Protected behavior:
- Core compute timestamps in UTC (`bar_start_utc`) for deterministic behavior.
- Display layer may present GMT+8, but cannot mutate compute semantics.

Primary files:
- `scripts/run_backtest.py` (UTC parsing/localization and summary metadata)
- `src/hongstr/backtest/engine.py` (UTC-indexed bars)
- `scripts/generate_regime_report.py` (UTC normalization before merges)
- `scripts/dashboard.py` (display and latest artifacts rendering)
- Tests:
  - `tests/test_timezone_alignment.py`
  - `tests/test_funding_schedule.py`

## E) Verification Pipeline Ownership (Objective 1 related)

Pipeline files requiring scripts/tests-only stabilization:
- `scripts/walkforward_suite.sh`
- `scripts/run_and_verify.sh`
- `scripts/verify_latest.py`
- `scripts/report_walkforward.py`
- tests:
  - `tests/test_walkforward_report.py`
  - `tests/test_gate_thresholds.py`

Observed contract gap:
- quick execution failure can still produce a stale `walkforward_latest` marked as completed, violating expected verify semantics.
