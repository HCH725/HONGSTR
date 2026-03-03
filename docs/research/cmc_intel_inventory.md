# CMC Intel Inventory

> Updated: 2026-03-03 | Scope: Binance Futures research metrics only | report_only

## Current research inventory

| Domain | Metric | Source | Symbols | History path | Status | Notes |
|---|---|---|---|---|---|---|
| Futures | `funding_rate` | Binance `/fapi/v1/fundingRate` | BTCUSDT, ETHUSDT, BNBUSDT | `data/derived/futures_metrics/<SYMBOL>/funding_rate/period=5m/*.jsonl` | Active | Earliest probed from 2020-01-01 forward |
| Futures | `open_interest_hist` | Binance `/futures/data/openInterestHist` | BTCUSDT, ETHUSDT, BNBUSDT | `data/derived/futures_metrics/<SYMBOL>/open_interest_hist/period=5m/*.jsonl` | Active | Rolling + chunked backfill |
| Futures | `global_long_short_account_ratio` | Binance `/futures/data/globalLongShortAccountRatio` | BTCUSDT, ETHUSDT, BNBUSDT | `data/derived/futures_metrics/<SYMBOL>/global_long_short_account_ratio/period=5m/*.jsonl` | Active | Rolling + chunked backfill |
| Futures | `premium_index` | Binance `/fapi/v1/premiumIndex` | BTCUSDT, ETHUSDT, BNBUSDT | `data/derived/futures_metrics/<SYMBOL>/premium_index/period=5m/*.jsonl` | Active | Snapshot-only REST; stored in 5m buckets |
| Futures | `liquidations` health probe | Binance `/fapi/v1/allForceOrders` | BTCUSDT, ETHUSDT, BNBUSDT | coverage only | WARN-tolerant | Endpoint currently returns maintenance; job must stay exit 0 |

## SSOT outputs

| File | Producer | Purpose |
|---|---|---|
| `data/state/futures_metrics_coverage_latest.json` | `scripts/futures_metrics_probe.py`, `scripts/futures_metrics_fetch.py`, `scripts/futures_metrics_backfill.py` | SSOT coverage for futures research metrics |
| `data/state/_futures_metrics_backfill_checkpoint.json` | `scripts/futures_metrics_backfill.py` | Resume pointer for manual backfill runs |

## CMC boundary

- CMC is explicitly out of scope for these futures metrics.
- Funding, OI, long/short ratios, premium, and liquidations health are sourced from Binance public futures endpoints only.
- `tg_cp` and dashboard consumers must continue to read `data/state/*` only; they must not fetch Binance or CMC directly.
