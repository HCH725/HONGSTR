# Obsidian Dashboards Exporter (report-only)

## Overview

`scripts/obsidian_dashboards_export.sh` renders report-only dashboard markdown pages from SSOT state JSON files.

Input is read-only under `data/state/`.

Output is written only to `_local/obsidian_vault/HONGSTR/Dashboards/`.

No writes are made to SSOT.

## Inputs

- `data/state/system_health_latest.json`
- `data/state/freshness_table.json`
- `data/state/coverage_matrix_latest.json`
- `data/state/brake_health_latest.json`
- `data/state/regime_monitor_latest.json`
- `data/state/data_catalog_latest.json` (optional)
- `data/state/changes_latest.json` (canonical alias from `scripts/state_snapshots.py`)

`data/state/changes_latest.json` is published from `data/state/data_catalog_changes_latest.json`.

Degrade rule for alias publication:

- If source exists and is readable, exporter consumes alias payload with deterministic summary.
- If source is missing or unreadable, `state_snapshots.py` still writes `changes_latest.json` with:
  - `ts_utc`
  - `status: WARN`
  - `reason: missing_source`
  - `changes: []`

## Outputs

- `_local/obsidian_vault/HONGSTR/Dashboards/10-HealthPack.md`
- `_local/obsidian_vault/HONGSTR/Dashboards/20-Freshness.md`
- `_local/obsidian_vault/HONGSTR/Dashboards/30-Coverage.md`
- `_local/obsidian_vault/HONGSTR/Dashboards/40-Brakes.md`
- `_local/obsidian_vault/HONGSTR/Dashboards/50-Regime.md`

Each page includes:

- generated_utc
- source paths
- summary bullets
- a markdown table

## Non-blocking behavior

- Missing or malformed input files are logged as `WARN`.
- Script exits with status code `0`.

## Manual run

```bash
cd /Users/hong/Projects/HONGSTR
bash scripts/obsidian_dashboards_export.sh
```

## Mirror to iCloud

Exporter writes to local Primary vault.

Then existing mirror publishes dashboards to iCloud mirror vault.

```bash
cd /Users/hong/Projects/HONGSTR
bash scripts/obsidian_dashboards_export.sh
OBSIDIAN_MIRROR_LOCK_DIR=/tmp/com.hongstr.obsidian_mirror.manual.lock bash scripts/obsidian_mirror_publish.sh
```

Expected iCloud target path:

`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/HONGSTR_MIRROR/Dashboards/`

## Kill switch

Disable exporter for one-shot run:

```bash
cd /Users/hong/Projects/HONGSTR
DASHBOARDS_EXPORT_ENABLED=0 bash scripts/obsidian_dashboards_export.sh
```

Disable mirror for one-shot run:

```bash
cd /Users/hong/Projects/HONGSTR
MIRROR_ENABLED=0 bash scripts/obsidian_mirror_publish.sh
```

## Validation

```bash
cd /Users/hong/Projects/HONGSTR
bash -n scripts/obsidian_dashboards_export.sh
.venv/bin/python -m pytest -q tests/test_obsidian_dashboards_export.py
bash scripts/obsidian_dashboards_export.sh
OBSIDIAN_MIRROR_LOCK_DIR=/tmp/com.hongstr.obsidian_mirror.manual.lock bash scripts/obsidian_mirror_publish.sh
```
