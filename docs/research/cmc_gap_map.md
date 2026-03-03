# CMC Gap Map

> Updated: 2026-03-03 | Principle: CMC does not own Binance Futures metric coverage

## Futures metrics source policy

| Metric | Primary source | CMC needed? | Current state | Next action |
|---|---|---|---|---|
| `funding_rate` | Binance `/fapi/v1/fundingRate` | No | Implemented | Expand backfill coverage over time |
| `open_interest_hist` | Binance `/futures/data/openInterestHist` | No | Implemented | Expand backfill coverage over time |
| `global_long_short_account_ratio` | Binance `/futures/data/globalLongShortAccountRatio` | No | Implemented | Expand backfill coverage over time |
| `premium_index` | Binance `/fapi/v1/premiumIndex` | No | Implemented | Keep rolling snapshots; no fake history |
| `liquidations` | Binance `/fapi/v1/allForceOrders` | No | Endpoint under maintenance | Keep WARN health probe until endpoint recovers |

## Explicit non-goals for CMC

- Do not use CMC for funding rates.
- Do not use CMC for open interest.
- Do not use CMC for long/short account ratios.
- Do not use CMC for premium index snapshots.
- Do not use CMC to paper over Binance endpoint maintenance.

## Remaining Binance-only gaps

| Priority | Metric | Endpoint family | Why it matters |
|---|---|---|---|
| P1 | Top trader long/short account ratio | Binance futures data | Distinguishes crowding in top accounts vs global accounts |
| P2 | Basis | Binance futures basis endpoint | Adds term-structure context for carry/regime work |
| P3 | Taker buy/sell volume | Binance futures data | Useful for aggression/flow imbalance studies |
| P4 | Liquidations event capture | Binance force orders | Enable once Binance restores the endpoint |
