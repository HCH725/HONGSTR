# Research SDK - Machine Learning Baseline

This document explains the Phase 4 Machine Learning integration within the HONGSTR Research SDK.

## Core Concepts

1. **Panel**: A strictly validated, multi-indexed DataFrame `(ts, symbol)` containing raw market prices (OHLCV). It ensures correct alignment.
2. **Factor / Feature**: Indicators derived from the Panel. We strictly use `shift(1)` for factors (like Moving Averages and True Range) to guarantee that they only depend on past data.
3. **Label**: The target variable we try to predict. We define a forward-looking horizon (e.g. 24 bars ahead). Labels represent the future outcome (`shift(-horizon)`).
4. **Look-ahead Bias**: The catastrophic error of letting the AI model learn from the future. We strictly negate this by using negative shifts on `labels` and positive shifts on `features`, and applying basic leakage checks to columns.

## ML Evaluation Method

Instead of typical K-fold Cross Validation which leaks future data, we use a chronological split:

- **In-Sample (IS)**: 2020-01-01 to 2024-12-31. Used for fitting the model.
- **Out-of-Sample (OOS)**: 2025-01-01 to Present.
- **Walkforward Validation**: We split the OOS period chronologically into 4 smaller chunks (folds) and measure the model stability as we roll forward.

## How Phase 4 Connects

This module generates:

1. `labels_{freq}.parquet` files containing target returns.
2. `dataset_{freq}_{h}.parquet` files mapping X (features) to y (labels).
3. `phase4_results.json` and `.md` covering prediction accuracy.

In future iterations, these trained baseline model weights can be invoked by the HONGSTR execution engine to emit signal artifacts!
