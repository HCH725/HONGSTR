# HONGSTR Research SDK (Panel/Factor MVP)

## Overview

This directory contains the independent **Research SDK** for the HONGSTR project. It is designed to provide a reproducible, reproducible, and standardized way to align historical data (Panels) and engineer features (Factors) without touching the core trading engine (`src/hongstr/`).

## Core Principles (Hard Rules)

1. **Zero Intrusion**: The research layer NEVER modifies the core pipeline (`src/hongstr/`), the matching semantics, the executor, or the dashboard.
2. **Stability-First Validation**: Gates ensure data quality (e.g., uniqueness, coverage, sortedness). Gate failures trigger `WARN` (exit code 0) but do not abort enclosing system scheduled tasks unless manually requested.
3. **Reproducibility**: Features output a `manifest.json` describing the row count, artifact hashes, and Git commits for strict auditing.
4. **No Look-ahead Bias**: Realized by separating the `factors` definitions with explicitly declared window and shift rules.

## Data Flow

```text
[data/derived/] 
   -> `research.panel.build_panel` 
   -> [reports/research/panels/*.parquet]
   -> `research.datasets.make_features` (applies FactorRegistry rules)
   -> [reports/research/features/*.parquet]
```

## Directory Structure

- `panel/`: Panel building logic (aligning multiple symbols and timeseries into a clean MultiIndex DataFrame) and Quality Gates.
- `factors/`: Pure-function feature definitions (Trends, Volatility, Breakouts).
- `datasets/`: Dataset builders integrating panels and factors.
- `experiments/`: Dedicated space for ML or strategy notebooks/scripts (Read their README).
- `tests/`: Automated unit tests for gate behaviors and dataset constraints.

## Execution

Use `scripts/build_features.sh` to trigger the end-to-end pipeline manually. It is not currently hooked into any `launchd` service.
