# HONGSTR Checkpoints (Phase 0)

This document tracks the completion of each work conversation in Phase 0.
MANDATORY: Update this file after each conversation (C1->C6).

## [C1] Repo Bootstrap + Governance

- **Date**: 2026-02-16 17:30 (GMT+8)
- **Built Items**:
  - Repo skeleton involved `src`, `tests`, `docs` structure.
  - Governance docs (`MASTER_SPEC.md`, `RUNBOOK.md`) established.
  - Python project config (`pyproject.toml`) with Ruff/Black/Pytest.
  - CI workflow (`.github/workflows/ci.yml`) for automated testing.
- **Files Changed**:
  - `docs/spec/MASTER_SPEC.md`
  - `docs/runbook/RUNBOOK.md`
  - `docs/checkpoints/phase0.md`
  - `.gitignore`, `.env.example`, `pyproject.toml`
  - `src/hongstr/__init__.py`
  - `tests/test_bootstrap.py`
  - `.github/workflows/ci.yml`
- **Config Keys**:
  - `BINANCE_API_KEY`, `BINANCE_API_SECRET`
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ALERT_CHAT_ID`
  - `AI_PRIMARY_PROVIDER`, `AI_PRIMARY_API_KEY`, `AI_BACKUP_PROVIDER`, `AI_BACKUP_API_KEY`
  - `OFFLINE_MODE`, `AUTO_OFFLINE_ENABLED`, `EXECUTION_MODE`
  - `FLASK_APP`, `FLASK_ENV`, `SECRET_KEY`
- **Verification**:
  - Lint: Passed (`ruff check .`)
  - Tests: Passed (`pytest`) - 2 tests passed.
  - Hygiene: `.env` ignored.
- **Risks**: None.
- **Next Actions**: Proceed to C2 (Data Pipeline)

## [C2] Data Pipeline

- **Date**: 2026-02-16 18:20 (GMT+8)
- **Built Items**:
  - `hongstr.data` package with `ingest`, `aggregate`, `quality` modules.
  - Implemented 1m ingestion from Binance Futures.
  - Implemented 5m/15m/1h/4h aggregation logic.
  - Data Quality Gate detection logic.
- **Files Changed**:
  - `src/hongstr/config.py`
  - `src/hongstr/data/ingest.py`
  - `src/hongstr/data/aggregate.py`
  - `src/hongstr/data/quality.py`
  - `tests/test_data_pipeline.py`
  - `scripts/dry_run_ingest.py`
  - `pyproject.toml` (added pyarrow, python-dotenv)
- **Config Keys**:
  - `DATA_DIR`
  - `SYMBOLS` (BTCUSDT, ETHUSDT, BNBUSDT)
  - `INTERVALS`
  - `TIMEZONE` (Asia/Taipei)
  - `STORAGE_FORMAT` (parquet)
- **Verification**:
  - Unit tests: Passed (`pytest tests/test_data_pipeline.py`) - 2 tests, 0 warnings.
  - Dry Run: Successfully fetched 60 1m klines for BTCUSDT, saved to parquet, verified file exists and readable.
  - Quality Gate: Verified missing data detection logic in tests.
- **Risks**:
  - Rate limiting logic is basic (fixed sleep), might need advanced handling for backfill.
  - Local parquet files for 5 years ~2GB/symbol, manageable.
- **Next Actions**: Proceed to C3 (Semantics + Backtest).

## [C2-HOTFIX] Verification & Timestamp Tools

- **Date**: 2026-02-16 18:40 (GMT+8)
- **Built Items**:
  - `scripts/inspect_timestamps.py`: Tool to audit parquet file timestamps and verify GMT+8 alignment.
  - `tests/test_timezone_alignment.py`: Unit test to prove UTC->GMT+8 conversion logic.
- **Files Changed**:
  - `scripts/inspect_timestamps.py`
  - `tests/test_timezone_alignment.py`
- **Verification**:
  - `pytest tests/test_timezone_alignment.py`: Passed.
  - `python3 scripts/inspect_timestamps.py`: Verified BTCUSDT start/end times are minute-aligned and correctly localized.
- **Decision**: Kept single `tests/test_data_pipeline.py` structure (Approach A) to avoid unnecessary churn.

## [C3] Semantics + Backtest

- **Date**: 2026-02-16 19:10 (GMT+8)
- **Built Items**:
  - `SemanticsV1` (core.py) with Fees (taker), Slippage (bps), Funding.
  - `BacktestEngine` (engine.py) with hedge mode support (simulated), funding accrual, and TP/SL.
  - `Metrics` (metrics.py) with Sharpe, CAGR, MaxDD, and OOS Splitting.
- **Files Changed**:
  - `src/hongstr/semantics/core.py`
  - `src/hongstr/backtest/engine.py`
  - `src/hongstr/backtest/metrics.py`
  - `tests/test_semantics.py`
  - `tests/test_backtest.py`
  - `scripts/smoke_backtest.py`
- **Semantics Version**: 1.0.0
- **Verification**:
  - Unit tests: Passed (`pytest tests/test_semantics.py tests/test_backtest.py`).
  - Smoke Test: Ran on BTCUSDT 1h data (from C2). Engine correctly executed trades, applied semantics, and generated OOS splits.
- **Known Limitations**:
  - Strategy signal stub is temporary.
  - Funding check is approximate (matches bar open time to 00/08/16 UTC).
- **Next Actions**: Proceed to C4 (Strategy Pool + Portfolio).

## [C3-HOTFIX] Funding Schedule UTC

- **Date**: 2026-02-16 19:35 (GMT+8)
- **Built Items**:
  - `SemanticsV1.is_funding_timestamp(ts)`: Centralized Funding Schedule logic (UTC 00/08/16).
  - `tests/test_funding_schedule.py`: Verification of UTC alignment.
- **Files Changed**:
  - `src/hongstr/semantics/core.py`
  - `src/hongstr/backtest/engine.py`
  - `tests/test_funding_schedule.py`
- **Verification**:
  - `pytest tests/test_funding_schedule.py`: Passed.
  - Smoke Test: Passed.

## [C4] Strategy Pool + Portfolio + Regime

- **Date**: 2026-02-16 20:20 (GMT+8)
- **Built Items**:
  - `StrategyRegistry` with HONG 1h/4h constraint enforcement.
  - Templates: `VWAPSupertrend`, `RSIMACD`, `BBRSI`.
  - `RegimeLabeler` (EMA50/200 on 4h).
  - `Selector` with Top3 Bull/Bear logic and JSON persistence.
- **Files Changed**:
  - `src/hongstr/strategy/core.py`
  - `src/hongstr/strategy/registry.py`
  - `src/hongstr/strategy/templates/initial.py`
  - `src/hongstr/portfolio/core.py`
  - `src/hongstr/regime/baseline.py`
  - `src/hongstr/selection/scoring.py`
  - `src/hongstr/selection/selector.py`
  - `tests/test_c4.py`
- **Verification**:
  - Unit tests (`tests/test_c4.py`) passed.
  - Demo scripts (`scripts/show_regime.py`, `scripts/show_hong_selection.py`) verified functionality.
- **Limitations**:
  - Regime labeling is simple EMA cross; no complex ML yet.
  - Selection uses manual policy, no auto-optimizer.
- **Next Actions**: Proceed to C5 (Execution + Reconcile + Alerts).

## [C5] Execution + Reconcile + Alerts

- **Date**: 2026-02-16 22:30 (GMT+8)
- **Built Items**:
  - `ExecutionEngine`: Modes A/B/C, Risk checks, Sizing, Bracket placement (SL first).
  - `Brokers`: PaperBroker (Simulated), BinanceFuturesTestnetBroker (Isolated Margin enforcement).
  - `Reconciler`: Orphan detection, Missing bracket detection.
  - `Alerts`: Telegram integration (INFO/WARN/CRIT).
- **Files Changed**:
  - `src/hongstr/config.py` (Added Execution/Risk/Alerts configs)
  - `src/hongstr/execution/` (models, broker, paper, binance_testnet, executor)
  - `src/hongstr/reconcile/reconciler.py`
  - `src/hongstr/alerts/telegram.py`
  - `scripts/fire_signal_demo.py`, `scripts/run_reconcile_loop.py`
  - `tests/test_execution.py`
- **Config Keys Added**:
  - `EXECUTION_MODE`, `OFFLINE_MODE`
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  - `MAX_CONCURRENT_POSITIONS`, `MAX_TOTAL_EXPOSURE_PCT`
  - `BINANCE_TESTNET_BASE_URL`
- **Verification**:
  - `pytest tests/test_execution.py`: Passed (covers orphans, offline mode, reduceOnly logic).
  - `fire_signal_demo.py`: Verified PaperBroker order flow.
- **Risks/Known Issues**:
  - Reconciler alerts on missing brackets but does not auto-repair (requires complex strategy context retrieval).
  - Binance Testnet execution requires valid API keys in `.env`.
- **Next Actions**: Proceed to C6 (Dashboard RWD).

## [C5-HOTFIX] Gates 1-3 (Artifact, Idempotency, Reconciliation)

- **Date**: 2026-02-16 23:30 (GMT+8)
- **Built Items**:
  - **Gate 1**: Strict `SelectionArtifact` validation (FAIL-CLOSED) + `PORTFOLIO_ID` check.
  - **Gate 2**: Bracket Idempotency (Checks existing SL/TP before placement).
  - **Gate 3**: Manual Close Handling (Reconciler cancels orphans if position closed manually).
- **Files Changed**:
  - `src/hongstr/selection/artifact.py` (New)
  - `src/hongstr/execution/executor.py` (Validation + Idempotency)
  - `src/hongstr/reconcile/reconciler.py` (Orphan logic)
  - `src/hongstr/config.py`
  - `tests/test_gate1_artifact.py`, `tests/test_gate2_idempotency` (in `test_execution.py`), `tests/test_gate3_manual_close.py`
- **Verification**:
  - Unit Tests: All passed (9 tests covering valid/invalid artifacts, idempotency, orphans).
  - Manual Scripts:
    - `fire_signal_demo.py`: Verified signal execution.
    - `run_reconcile_loop.py`: Verified orphan detection.
- **Next Actions**: Proceed to C6 (Dashboard).
