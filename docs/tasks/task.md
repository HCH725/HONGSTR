# Task: Phase 1 C7 - Real-time Data Feeds (Binance WebSocket)

- [x] 0. Precheck (repo + env)
- [x] 1. Create Module Skeleton
- [x] 2. Install Dependencies
- [x] 3. Implementation (C7)
  - [x] Types
  - [x] Binance WS Stream Manager
  - [x] Persistence
  - [x] Observability
- [x] 4. Config Keys
- [x] 5. Script: Run WS (Smoke Test)
- [x] 6. Tests
- [x] 7. Docs / Checkpoint
- [x] 8. Final Verify
- [x] 9. Commit

## Task: Phase 1 C8 - Signal Engine (Realtime Buffering & Strategy)

- [x] 0. Create Module Skeleton (src/hongstr/signal)
- [x] 1. Implement Buffer & Resampling (1m -> 1h/4h)
- [x] 2. Implement Signal Engine (Strategy Integration)
- [x] 3. Implement Persistence (data/signals/)
- [x] 4. Tests (Buffer, Engine, Persistence)
- [x] 5. Smoke Script (run_signal_engine.py)
- [x] 6. Final Verify & Commit

## Task: Phase 1 C9 - Strategy Implementation

- [x] 0. Preflight & Skeleton (src/hongstr/signal/strategies)
- [x] 1. Config Updates (Strategy Params)
- [x] 2. Implement Indicators (src/hongstr/signal/indicators.py)
- [x] 3. Implement Strategies (VWAP Supertrend, RSI Div, MACD Div)
- [x] 4. Wire Strategies into Engine
- [x] 5. Tests (Indicators, Strategies, Engine)
- [x] 6. Smoke Scripts (run_signal_strategies.py, smoke_c9.sh)
- [x] 7. Verification & Docs
- [x] 8. Commit & Tag

## Task: Phase 1 C10 - Execution Bridge (Signal -> Executor)

- [x] 0. Config Updates (Execution Modes, Review)
- [x] 1. Create Bridge Module (src/hongstr/bridge/signal_to_execution.py)
- [x] 2. Create Runner Script (scripts/run_bridge.py)
- [x] 3. Create Tests (tests/test_bridge.py)
- [x] 4. Smoke Test & Verify
- [x] 5. Tag v0.10-c10

## Task: Phase 1 C11 - Risk Management (Execution Guardrails)

- [x] 1. Config Updates (Risk Parameters)
- [x] 2. Create Risk Module (src/hongstr/execution/risk.py)
- [x] 3. Update Executor (Integrate Risk Checks)
- [x] 4. Unit Tests (tests/test_risk_manager.py)
- [x] 5. Smoke Test (scripts/smoke_c11.sh - Allow/Reject Scenarios)
- [x] 6. Tag v0.11-c11

## Task: Phase 1 C12 - Exchange Safety + Semantics (Testnet)

- [x] 1. Create Exchange Filters (src/hongstr/execution/exchange_filters.py)
- [x] 2. Config Updates (Hedge Mode, Brackets)
- [x] 3. Update BinanceBroker (Support reduceOnly, positionSide, Rounding)
- [x] 4. Update Executor (Entry->Bracket Flow, Close Logic)
- [x] 5. Unit Tests (tests/test_exchange_filters.py)
- [x] 6. Smoke Test Paper (scripts/smoke_c12_paper.sh)
- [ ] 7. Smoke Test Testnet (scripts/smoke_c12_testnet.sh)
- [ ] 8. Tag v0.12-c12
