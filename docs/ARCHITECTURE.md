# HONGSTR Architecture

HONGSTR is designed as a modular pipeline for algorithmic trading research and execution.

## Design Philosophy

1. **Determinism**: Identical inputs must yield identical outputs in backtesting.
2. **Safety**: Execution is dry-run by default with multiple validation gates.
3. **Auditability**: Every decision and trade is logged with its source context.

## System Layers

### Data Layer

- **Ingestion**: `scripts/ingest_historical.py`
- **Storage**: Parquet for high-speed columnar access.

### Logic Layer

- **Strategy Engine**: Modular strategy classes in `src/hongstr/strategy/`.
- **Backtest Engine**: Fast vector/event hybrid in `src/hongstr/backtest/engine.py`.

### Analysis Layer

- **Quality Gate**: Validates Sharpe, MDD, and trade frequency.
- **Walk-Forward**: Out-of-Sample verification suite.

### Execution Layer

- **Broker Interface**: Abstract base classes in `src/hongstr/execution/broker.py`.
- **Binance Testnet**: Hardened HMAC signing with URL-only payload delivery.

## Key Data Flows

For a detailed breakdown of the data lifecycle, see [docs/handoff/01_system_overview.md](file:///Users/hong/Projects/HONGSTR/docs/handoff/01_system_overview.md).
