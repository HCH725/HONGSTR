# CMC Market Intel P1 Integration

## Overview

This document outlines the Phase 1 integration of CoinMarketCap (CMC) Market Intelligence into the HONGSTR research platform. Specifically, this captures **Narratives** and **Macro Events** data.

This integration **does not** replace or overlap with exchange-level data (OHLCV, Funding Rates, Open Interest, Liquidations). It purely captures CMC's unique, high-level structural data.

## Execution

To run the fetcher and sync the data catalog:

1. Ensure `.env` contains `CMC_API_KEY`.
2. Run the fetch script:

   ```bash
   python3 scripts/cmc_market_intel_fetch.py
   ```

3. Sync state:

   ```bash
   bash scripts/refresh_state.sh
   ```

## Expected Outputs

- **Data (Derived)**: JSON files in `data/derived/cmc/market_intel/narratives/` and `macro_events/`.
- **Manifests**: `reports/state_atomic/manifests/cmc_market_intel_v1.json` is generated for the indexers.
- **Coverage State**: `data/state/cmc_market_intel_coverage_latest.json` indicates whether the latest fetch was OK, WARN (empty payload), or FAIL.
- **Data Catalog**: The new dataset `cmc_market_intel_v1` is reflected in `data/state/data_catalog_latest.json` after running `scripts/refresh_state.sh`. `data/state/data_catalog_changes_latest.json` will show the structural addition.

## Empty Payloads & Stubs

CMC macro event endpoints or high tier calls may return empty depending on API tier or if data doesn't exist. This integration gracefully handles empty returns by assigning a `WARN` status to coverage telemetry ensuring pipelines don't crash while retaining data audit trails.
