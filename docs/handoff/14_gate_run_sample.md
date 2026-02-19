# Gate Run Sample (2026-02-18)

Source: `/Users/hong/Projects/HONGSTR/reports/gate_latest.md`

## Protected File Semantics (Machine-Readable)

- Protected files touched in THIS commit? NO
- Protected files changed in working tree (uncommitted)? YES
- Notes: `git show --name-only 3ba186a` and `git diff --name-only HEAD~1..HEAD` contain no `src/hongstr/backtest/**` or `src/hongstr/execution/**`. Current working tree still has pre-existing edits under those paths.

## How To Determine

- THIS commit: `git show --name-only --pretty="" <commit>` and `git diff --name-only HEAD~1..HEAD`
- Working tree: `git status --porcelain`

## Exchange Smoke WARN -> PASS (No secrets in repo)

Run:

1. `bash scripts/bootstrap_dev_env.sh`
2. `cp .env.example .env`
3. Edit `.env` locally and fill only:
   - `BINANCE_API_KEY`
   - `BINANCE_API_SECRET`
4. `export $(grep -v '^#' .env | xargs)`
5. Verify first with public endpoint:
   - `python3 scripts/exchange_smoke_test.py --mode TIME --timeout_sec 20 --debug_signing`
6. Then run gate:
   - `bash scripts/gate_all.sh`

## How to rerun FAILED windows and update latest when fixed

1. Inspect failed windows from the per-run report:
   - `cat reports/walkforward/<RUN_ID>/walkforward.json`
2. Preview rerun commands:
   - `bash scripts/rerun_failed_windows.sh --report_json reports/walkforward/<RUN_ID>/walkforward.json --dry-run`
3. Execute rerun:
   - `bash scripts/rerun_failed_windows.sh --report_json reports/walkforward/<RUN_ID>/walkforward.json`
4. Verify latest pointer:
   - Success run prints `LATEST_UPDATED ... latest_json=reports/walkforward_latest.json`
   - `reports/walkforward_latest.json` should match the new successful `run_id`

```markdown
# Gate All Report

- Timestamp (UTC): 2026-02-18T14:30:17Z
- Git Commit: 3ba186a
- Python: python3
- Strict Mode: 0
- Overall: WARN
- Exit Code: 0
- Stop Reason: none
- Log: /Users/hong/Projects/HONGSTR/logs/gate_all_20260218_143017.log

## Env Precheck
- python --version: Python 3.9.6
- python -m pytest --version: pytest 8.4.2
- python -m ruff --version: ruff 0.15.1
- BINANCE_FUTURES_TESTNET: 0
- BINANCE_TESTNET: 0
- reports/walkforward_latest.json: present
- data/backtests latest run_dir: /Users/hong/Projects/HONGSTR/data/backtests/2026-02-18/20260218_222933_4b3c

## Protected Touch Status
- Protected touched THIS commit?: NO
- Protected changed in working tree?: YES

## Status Summary
- WARN count: 5
- FAIL count: 0
- SKIP count: 1

## Step Results
- python -m ruff check .: WARN (rc=1; reason=lint debt (pre-existing))
- python -m ruff check <changed_paths>: WARN (rc=1; reason=lint debt on changed paths)
- python -m pytest -q -m "not integration": PASS (rc=0; reason=ok)
- bash scripts/smoke_backtest.sh: PASS (rc=0; reason=ok)
- bash scripts/walkforward_suite.sh --quick --symbols BTCUSDT: SKIP (rc=1; reason=insufficient local data for configured windows)
- python3 scripts/report_walkforward.py: PASS (rc=0; reason=ok)
- walkforward latest pointer update: WARN (rc=0; reason=LATEST_NOT_UPDATED_STALE_RISK failed_windows=BULL_2021_H1,BEAR_2022)
- resolve latest run_dir for selection: PASS (rc=0; reason=resolved /Users/hong/Projects/HONGSTR/data/backtests/2026-02-18/20260218_223033_46fb)
- python3 scripts/generate_selection_artifact.py --run_dir <latest>: PASS (rc=0; reason=ok)
- python3 scripts/generate_action_items.py: PASS (rc=0; reason=ok)
- python3 scripts/exchange_smoke_test.py --debug_signing: WARN (rc=1; reason=ENV_MISSING_KEYS)
- python3 scripts/execute_paper.py --debug_signing: PASS (rc=0; reason=ok)
- python3 scripts/order_reconcile.py: PASS (rc=0; reason=ok)
- secret leak scan: PASS (rc=0; reason=ok)

## Remediation
- ruff debt (pre-existing): python3 -m ruff check . --statistics
- ruff focused (changed files): python3 -m ruff check <changed_paths>
- ruff install: python3 -m pip install -e ".[dev]" || python3 -m pip install ruff
- ruff changed paths detail: python3 -m ruff check scripts/dashboard.py scripts/generate_regime_report.py scripts/run_and_verify.sh tests/test_backtest.py tests/test_backtest_deterministic.py tests/test_bridge.py tests/test_execution.py tests/test_signal_engine_io.py
- walkforward latest pointer: inspect reports/walkforward/20260218_143032_3ba186a
- walkforward rerun: bash scripts/walkforward_suite.sh --quick --symbols BTCUSDT
- walkforward report rerender: python3 scripts/report_walkforward.py --run_id 20260218_143032_3ba186a
- exchange smoke env: export BINANCE_API_KEY=... && export BINANCE_API_SECRET=...
- exchange smoke template: cp .env.example .env && export $(grep -v '^#' .env | xargs)
```
