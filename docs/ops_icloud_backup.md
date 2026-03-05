# iCloud Daily Cold Backup (Full Recovery)

## Overview

`scripts/icloud_backup_run.sh` performs a non-blocking daily backup of recovery-critical repository and state assets to iCloud Drive.

Target root:

`~/Library/Mobile Documents/com~apple~CloudDocs/HONGSTR_BACKUP/`

Collections:

- `latest/` for fast restore from most recent copy
- `snapshots/YYYY-MM-DD/` for daily history

The backup flow is copy-only. It does not write to `data/state/**` producers and does not change SSOT writer ownership.

## Scope (allowlist)

- `scripts/`
- `docs/`
- `launchd/`
- `web/` (if present)
- `_local/obsidian_vault/HONGSTR/KB/`
- `_local/obsidian_vault/HONGSTR/Dashboards/`
- `data/state/`
- `reports/state_atomic/`
- `data/derived/`
- `data/backtests/`

## Exclusions

Backup excludes are enforced across all allowlist paths:

- `.git/`
- `node_modules/`
- `.venv/`
- `dist/`
- `__pycache__/`
- `.env`, `.env.*`
- `*token*`, `*secret*`
- `*.key`, `id_rsa`, `id_rsa.pub`, `.ssh/`
- `*keychain*`, `*Browser*`
- `*.parquet`, `*.pkl`, `*.pickle`

## Manifest and Hashes

Each successful run writes in both `latest/` and daily snapshot folder:

- `manifest.json`
  - `ts_utc`
  - `mode`
  - `counts`
  - `bytes`
  - `source_root`
  - `target_root`
  - `excludes_summary`
- `sha256sums.txt`
  - includes hash for `manifest.json`
  - includes hash for selected small key files to support quick integrity checks

## Environment Variables

- `BACKUP_ENABLED` default `1`; set `0` for no-op
- `BACKUP_MODE` default `full`; supports `full|incremental`
- `BACKUP_ROOT` default iCloud backup root above
- `BACKUP_RETENTION_DAYS` default `0` (keep forever)
- `BACKUP_DRY_RUN` default `0`; set `1` to preview rsync changes without writing backup artifacts

## Manual Run

```bash
cd /Users/hong/Projects/HONGSTR
bash scripts/icloud_backup_run.sh
```

Dry run:

```bash
cd /Users/hong/Projects/HONGSTR
BACKUP_DRY_RUN=1 BACKUP_ROOT=/tmp/hongstr_backup_preview bash scripts/icloud_backup_run.sh
```

## launchd

Install daily 08:30 job:

```bash
cd /Users/hong/Projects/HONGSTR
bash scripts/install_icloud_backup_launchd.sh install
bash scripts/install_icloud_backup_launchd.sh status
```

## Restore SOP (new machine)

1. Install Git, Python, and required runtime dependencies.
2. Copy backup content from iCloud Drive `HONGSTR_BACKUP/latest/` to local workspace.
3. Verify `manifest.json` and `sha256sums.txt`.
4. Recreate virtual environment and dependencies as needed.
5. Reinstall launchd jobs from `launchd/` and installer scripts.
6. Run:
   - `bash scripts/refresh_state.sh`
   - `bash scripts/obsidian_dashboards_export.sh`
7. Confirm dashboards and state outputs are available.

## Risks

- iCloud sync lag can delay availability of newest snapshot.
- Very large history under `data/backtests/` can increase sync duration.
- If iCloud is unavailable, run logs WARN and exits `0`; no upstream jobs are blocked.

## Kill Switch

- One-shot disable:
  - `BACKUP_ENABLED=0 bash scripts/icloud_backup_run.sh`
- Scheduled disable:
  - `bash scripts/install_icloud_backup_launchd.sh uninstall`

## Non-blocking Guarantee

Backup errors are WARN-only and script exits `0` to avoid blocking data/control/research workflows.
