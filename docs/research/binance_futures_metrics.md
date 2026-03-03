# Binance Futures Metrics SOP

This workflow is research-only. It writes raw metric rows into gitignored `data/derived/**` and writes coverage state into `data/state/futures_metrics_coverage_latest.json`. It does not touch `src/hongstr/**`, trading execution, or Telegram commands.

## Daily rolling job

Use the rolling fetcher for the normal data-plane cadence:

```bash
bash scripts/futures_metrics_daily.sh \
  --metrics funding_rate open_interest_hist global_long_short_account_ratio premium_index
```

- Rolling mode fetches only recent windows, not full history.
- Historical metrics reuse the stored `earliest_utc` from coverage when available.
- The script always refreshes the liquidations health probe unless `--skip-liquidations-probe` is set.

## Earliest probe

Run this before a first backfill, or any time you want to refresh `earliest_utc` coverage:

```bash
python3 scripts/futures_metrics_probe.py \
  --symbols BTCUSDT ETHUSDT BNBUSDT \
  --metrics funding_rate open_interest_hist global_long_short_account_ratio premium_index liquidations \
  --start-date 2020-01-01
```

- If Binance starts later than `2020-01-01`, the coverage file records the true earliest available timestamp.
- `premium_index` is snapshot-only and records the current 5m bucket.
- `liquidations` is health-probe only. If Binance returns maintenance, coverage records `status=WARN` and `reason=maintenance`.

## Manual backfill

Use backfill only as a manual or one-shot job. Do not schedule this in the daily loop.

```bash
python3 scripts/futures_metrics_backfill.py \
  --symbols BTCUSDT ETHUSDT BNBUSDT \
  --metrics funding_rate open_interest_hist global_long_short_account_ratio \
  --start-date 2020-01-01 \
  --chunk-days 7
```

- Resume state is stored in `data/state/_futures_metrics_backfill_checkpoint.json`.
- Re-running the same range is safe because storage writes dedupe by `ts_utc` + `event_time_ms`.
- Use `--max-windows 1` for a short smoke run.

## How to inspect coverage

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path("data/state/futures_metrics_coverage_latest.json")
payload = json.loads(path.read_text(encoding="utf-8"))
for row in payload.get("rows", []):
    print(
        row["symbol"],
        row["metric"],
        row["status"],
        row["earliest_utc"],
        row["latest_utc"],
        row["reason"],
    )
PY
```

Look for:

- `earliest_utc`: earliest probe result, not fake `2020-01-01`.
- `latest_utc`: latest locally stored row or current snapshot.
- `storage_earliest_utc` and `storage_latest_utc`: what is actually on disk.
- `status` and `reason`: operational health, including liquidations maintenance.
