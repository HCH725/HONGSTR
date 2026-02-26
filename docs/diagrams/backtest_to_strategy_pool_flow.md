# HONGSTR Strategy Lifecycle Flow

This document describes the end-to-end data and decision flow from raw market data ingestion to strategy control.

## Flow Diagram

```mermaid
flowchart TD
    subgraph DataPlane ["Data Plane (Batch/ETL)"]
        A[Binance API] -- scripts/daily_etl.sh --> B[data/derived/SYMBOL/1m/*.jsonl]
    end

    subgraph StatePlane ["State Plane (Atomic Snapshot)"]
        B -- bash scripts/refresh_state.sh --> C[data/state/*.json]
        C1[freshness_table.json]
        C2[coverage_matrix_latest.json]
    end

    subgraph ResearchPlane ["Research Plane (Simulation)"]
        B -- research/loop/research_loop.py --> D[reports/backtests/YYYY-MM-DD/ID/]
        D1[summary.json]
        D2[selection.json]
        D3[gate.json]
    end

    subgraph SelectionPlane ["Strategy Pool (Promotion)"]
        D -- src/hongstr/selection/selector.py --> E[data/state/strategy_pool.json]
        D -- data/state/_research/leaderboard_update.sh --> F[data/state/_research/leaderboard.json]
        E -- scripts/dashboard.py --> G[Dashboard Metrics]
    end

    subgraph ControlPlane ["Control Plane (Telegram CP)"]
        E -- tg_cp_server.py /skills --> H[Telegram Bot]
        F -- tg_cp_server.py /run leaderboard_query --> H
        H -- User Commands --> I[Status/Audit Replies]
    end

    B -.-> D
    C -.-> D
    E -.-> H
```

## Key Components

- **Data Plane**: Canonical source of truth for backtesting and signal generation.
- **Research Plane**: Where candidate strategies are simulated and artifacts (DoD/Gate) are produced.
- **State Plane**: Global system health and data availability monitors.
- **Strategy Pool**: The active "Shelf" of strategies authorized for monitoring or execution.
- **Control Plane**: Human-in-the-loop audit and management interface via Telegram.

---
*Red Line Policy: core diff=0 | report_only | tg_cp no-exec | data/**gitignored*
