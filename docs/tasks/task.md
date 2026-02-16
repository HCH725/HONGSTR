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

- [ ] 0. Preflight & Skeleton (src/hongstr/signal/strategies)
- [ ] 1. Config Updates (Strategy Params)
- [ ] 2. Implement Indicators (src/hongstr/signal/indicators.py)
- [ ] 3. Implement Strategies (VWAP Supertrend, RSI Div, MACD Div)
- [ ] 4. Wire Strategies into Engine
- [ ] 5. Tests (Indicators, Strategies, Engine)
- [ ] 6. Smoke Scripts (run_signal_strategies.py, smoke_c9.sh)
- [ ] 7. Verification & Docs
- [ ] 8. Commit & Tag
