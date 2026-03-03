# Data Catalog And Auto Changelog

This repo now tracks dataset inventory via producer-written manifests and a canonical state-plane catalog.

## Files and ownership

| Path | Writer | Purpose |
|---|---|---|
| `reports/state_atomic/manifests/<dataset_id>.json` | Individual producers | Stable machine-readable dataset manifest |
| `reports/state_atomic/data_catalog_scan.json` | `scripts/state_atomic/data_catalog_scan.py` | Atomic manifest scan output with skipped-file warnings |
| `data/state/data_catalog_latest.json` | `scripts/state_snapshots.py` | Canonical data catalog for consumers |
| `data/state/data_catalog_changes_latest.json` | `scripts/state_snapshots.py` | Canonical “what changed” diff vs previous catalog |
| `data/state/_history/data_catalog_prev.json` | `scripts/state_snapshots.py` | Previous catalog snapshot used for diffing |

All of the runtime files above are gitignored under `data/**` and `reports/**`.

## Producer contract

When a producer successfully lands a dataset, it should atomically write one manifest:

- Path: `reports/state_atomic/manifests/<dataset_id>.json`
- Write mode: temp file + rename
- Schema: fixed keys only (`dataset_id`, `schema_version`, `producer`, `cadence`, `path_patterns`, `symbols`, `metrics`, `periods`, `sources`, `provenance`, `notes`)

The Binance Futures metrics producers currently emit `reports/state_atomic/manifests/futures_metrics.json`.

## Refresh flow

Run the normal read-only refresh:

```bash
bash scripts/refresh_state.sh
```

The refresh now includes:

1. `scripts/state_atomic/data_catalog_scan.py`
2. `scripts/state_snapshots.py`

If a manifest is missing or malformed, the scan skips it, records a warning in `reports/state_atomic/data_catalog_scan.json`, and the overall refresh still exits successfully.

## How to verify “what’s new”

Inspect the canonical files:

```bash
python3 - <<'PY'
import json
from pathlib import Path

catalog = json.loads(Path("data/state/data_catalog_latest.json").read_text(encoding="utf-8"))
changes = json.loads(Path("data/state/data_catalog_changes_latest.json").read_text(encoding="utf-8"))

print("datasets:", [row["dataset_id"] for row in catalog.get("datasets", [])])
print("added:", changes.get("added_datasets"))
print("updated:", changes.get("updated_datasets"))
print("removed:", changes.get("removed_datasets"))
PY
```

Interpretation:

- First run: `prev_ts_utc` is `null`; all current datasets appear under `added_datasets`.
- Later runs: only real structural changes appear under `updated_datasets`.
- Routine `provenance.generated_utc` refreshes do not create noisy updates.

## Daily report summary

`data/state/daily_report_latest.json` now exposes a one-line summary under:

- `ssot_components.data_catalog_changes.summary`

Examples:

- `Dataset changes: initial +1, ~0, -0`
- `Dataset changes: +0, ~1, -0`
- `Dataset changes: UNKNOWN`
