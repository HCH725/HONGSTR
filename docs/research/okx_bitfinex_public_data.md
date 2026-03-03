# OKX + Bitfinex Public Data (P0)

This flow captures a small public-data baseline from OKX and Bitfinex for cross-exchange divergence research. It complements the existing Binance Futures metrics pipeline instead of duplicating it.

## What it fetches

### OKX

- `open_interest`
  - Endpoint: `GET /api/v5/public/open-interest`
  - Scope: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `BNB-USDT-SWAP`
- `long_short_ratio`
  - Endpoint: `GET /api/v5/rubik/stat/contracts/long-short-account-ratio`
  - Scope: `BTC`, `ETH`, `BNB`

### Bitfinex

- `liquidations_latest`
  - Endpoint: `GET /v2/liquidations/hist`
- `deriv_status_hist`
  - Endpoint: `GET /v2/status/deriv/ALL/hist`

## Why this is different from Binance futures metrics

- Binance Futures metrics are exchange-native futures risk factors for the Binance venue itself.
- OKX + Bitfinex P0 adds cross-exchange reference points.
- The main research use here is divergence analysis: comparing OI / account-ratio / liquidation structure across venues instead of re-fetching the same Binance-only signals.

## Runtime storage (gitignored)

### OKX

- `data/derived/okx/public/open_interest/<INST_ID>/<ts_utc>.json`
- `data/derived/okx/public/long_short_ratio/<SYMBOL>/<ts_utc>.json`

### Bitfinex

- `data/derived/bitfinex/public/liquidations_latest/latest/<ts_utc>.json`
- `data/derived/bitfinex/public/deriv_status_hist/ALL/<ts_utc>.json`

### Atomic producer outputs

- `reports/state_atomic/okx_public_coverage.json`
- `reports/state_atomic/bitfinex_public_coverage.json`
- `reports/state_atomic/manifests/okx_public_v1.json`
- `reports/state_atomic/manifests/bitfinex_public_v1.json`

### Canonical state outputs

- `data/state/okx_public_coverage_latest.json`
- `data/state/bitfinex_public_coverage_latest.json`
- `data/state/data_catalog_latest.json`
- `data/state/data_catalog_changes_latest.json`

## How to run

### Rolling fetch

```bash
python3 scripts/okx_public_fetch.py
python3 scripts/bitfinex_public_fetch.py
```

Both scripts:

- use public endpoints only
- retry with timeout/backoff
- keep exit code `0` even if an endpoint fails or returns an empty array
- record failure/empty conditions in coverage instead of crashing

### Refresh canonical state

```bash
bash scripts/refresh_state.sh
```

This step:

1. scans manifests into the data catalog flow
2. writes canonical `data/state/*` snapshots
3. updates `data_catalog_changes_latest.json` automatically

## How to inspect coverage

```bash
python3 - <<'PY'
import json
from pathlib import Path

for name in ("okx_public_coverage_latest.json", "bitfinex_public_coverage_latest.json"):
    path = Path("data/state") / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    print(name, payload["ts_utc"])
    for row in payload.get("rows", []):
        print(" ", row["dataset"], row["key"], row["status"], row["rows"], row["reason"])
PY
```

Interpretation:

- `OK`: endpoint returned non-empty JSON rows
- `WARN`: endpoint returned a valid empty array (or another non-blocking condition)
- `FAIL`: request failed after retries

An empty array is valid JSON for Bitfinex here. It must be recorded in coverage, not treated as a crash.
