# HONGSTR Data Plane (Unified Fetch + State Refresh)

`com.hongstr.data_plane` is the single scheduled local data-plane job for research data ingestion. It runs fetchers first, then publishes canonical `data/state` through the existing state plane.

## What It Runs

Manual or scheduled runs use one entrypoint:

```bash
bash scripts/data_plane_run.sh
```

The runner executes these steps in order:

1. `python3 scripts/futures_metrics_daily.py`
2. `python3 scripts/okx_public_fetch.py`
3. `python3 scripts/bitfinex_public_fetch.py`
4. `python3 scripts/cmc_market_intel_fetch.py`
5. `bash scripts/refresh_state.sh`

The first four steps are non-blocking. If one fetcher fails, the runner prints `WARN`, records the step exit code, and continues. `refresh_state.sh` remains the canonical publication step for `data/state`; if it fails, the overall run fails.

Each fetcher step is also bounded by a soft timeout (`DATA_PLANE_STEP_TIMEOUT_SEC`, default `45`) so a stuck upstream request does not hold the whole schedule indefinitely.

## Writer Boundary

- Fetchers write only to `data/derived/**` and `reports/state_atomic/**`.
- `data/state/**` is refreshed only by `scripts/state_snapshots.py`, reached via `bash scripts/refresh_state.sh`.
- Consumers such as `tg_cp` and the dashboard remain SSOT-only readers of `data/state/**`.

## Covered Sources

- Binance Futures rolling metrics (`futures_metrics_daily.py`)
- OKX public derivatives snapshots (`okx_public_fetch.py`)
- Bitfinex public derivatives snapshots (`bitfinex_public_fetch.py`)
- CMC market intel (`cmc_market_intel_fetch.py`)

CMC may legitimately return `WARN` when `CMC_API_KEY` is absent or a tier-gated endpoint is unavailable. That warning is non-blocking for the data plane.

## launchd Schedule

The LaunchAgent template lives at:

```bash
ops/launchagents/com.hongstr.data_plane.plist
```

Default schedule is local time `06:00` every day.

Install, remove, or inspect the LaunchAgent with:

```bash
bash scripts/install_data_plane_launchd.sh install
bash scripts/install_data_plane_launchd.sh status
bash scripts/install_data_plane_launchd.sh uninstall
```

The rendered plist is installed to `~/Library/LaunchAgents/com.hongstr.data_plane.plist`.

## Logs

The job writes launchd stdout/stderr logs to:

```bash
logs/launchd_data_plane.out.log
logs/launchd_data_plane.err.log
```

Quick inspection:

```bash
tail -n 200 logs/launchd_data_plane.out.log
tail -n 200 logs/launchd_data_plane.err.log
```

## How To Verify Output

After a run, inspect:

- `data/state/data_catalog_latest.json`
- `data/state/data_catalog_changes_latest.json`
- `data/state/futures_metrics_coverage_latest.json`
- `data/state/okx_public_coverage_latest.json`
- `data/state/bitfinex_public_coverage_latest.json`
- `data/state/cmc_market_intel_coverage_latest.json`
- `data/state/daily_report_latest.json`

These are the SSOT surfaces for manifests, coverage, and daily summary reporting.
