# HONGSTR MASTER SPECIFICATION (Phase 0)

> **SINGLE SOURCE OF TRUTH**
> This document is the ONLY authoritative spec. If a requirement is missing, propose a SPEC PATCH.

## 1. Non-Negotiables (Must Never Be Violated)

### A) Time/Timezone
- **Internal Time Basis**: GMT+8 (Asia/Taipei).
- All bar alignment and logging must use GMT+8.

### B) Data Single Source
- **Raw Market Data**: ONLY 1m klines from Binance official sources (2020-01-01 -> now).
- **Derived Timeframes**: MUST be aggregated from 1m (v1 materialize: 5m / 15m / 1h / 4h).
- **Constraint**: No mixed-source klines; no separate downloads for derived frames.

### C) Single Semantics Layer (Versioned)
- All trading logic components must use a central semantics layer for:
  - Funding calculations
  - Fee models
  - Slippage simulation
  - Contract rules
  - Settlement alignment
- **Versioning**: Any change MUST bump `backtest_semantics_version` and mark coverage `NEEDS_REBASE`.

### D) HONG Strategy Policy
- **Bias**: Trend-biased.
- **Allowed Timeframes**: 1h and 4h ONLY (Phase 0).

### E) Multi-Portfolio Isolation
- `portfolio_id` is MANDATORY in all signal, order, execution, pool, and health events.
- **LAB Portfolios**: Must NOT contaminate HONG pool/candidates. Strict isolation.

### F) Execution Safety
- **Mode**: Hedge mode (long/short both allowed).
- **Order Types**:
  - Entry: Market.
  - TP/SL: Limit orders (ReduceOnly).
- **Valuation**: TP/SL MUST be based on actual fill `avg_price` & `filled_qty`.
- **Slippage**: V1 model must be applied consistently in backtest/sim.
- **Exchange Constraints**: Min notional, step size, tick size must be validated. Rejects must emit clear events.

### G) Margin Mode
- **Futures Margin**: MUST be ISOLATED (逐倉). Cross margin is FORBIDDEN.
- **Policy**: Do not prevent system startup if Cross is detected. Instead:
  - Block execution for (portfolio_id, symbol).
  - Emit Telegram WARN.
  - Auto-recover (unblock) when fixed.

### H) External Intervention
- Detect manual changes in Binance app via reconcile.
- Cancel stale brackets.
- Mark intent as canceled externally.
- Emit INFO/WARN events.

### I) UNPROTECTED Handling
- **Scenario**: TP/SL missing after entry.
- **Mode B + Failsafe**:
  - Enter PROTECT mode (block new entries).
  - Bounded retry/backoff.
  - If exceeds `MAX_UNPROTECTED_SEC` or `RETRY_MAX` -> `reduceOnly` market flatten + halt.
  - Emit CRITICAL alert.

### J) OFFLINE MODE (Graceful Degradation)
- `OFFLINE_MODE=true` forces:
  - No ingest/update from Binance.
  - `execution_mode=DRYRUN` only.
  - Telegram disabled (log-only).
  - Backtest/Analysis/ML local features OK.
- **Auto-Offline**: Enter offline after N failed health checks. Recover after M=5 successes.

### K) Secrets & Hygiene
- All keys in `.env` only.
- Never commit secrets.
- CI must include secret scanning.

## 2. Directory Structure Scope
- `docs/`: Governance, specs, runbooks.
- `src/`: Application source code.
- `tests/`: Unit and integration tests.
- `scripts/`: Utilities (formatting, lightweight tools).
- `.github/`: CI configurations.
