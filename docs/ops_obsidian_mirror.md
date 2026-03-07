# Obsidian iCloud Mirror Publisher

## Overview

`com.hongstr.obsidian_mirror` runs `scripts/obsidian_mirror_run.sh` once per day and performs an export-then-mirror chain from the local source vault to the iCloud Obsidian mirror vault `HONGSTR_MIRROR`.

Current launchd chain uses `scripts/obsidian_mirror_run.sh`:

1. Export dashboards from SSOT: `scripts/obsidian_dashboards_export.sh`
2. Publish mirror to iCloud: `scripts/obsidian_mirror_publish.sh`

This mirror is governance-only and non-blocking:

- It does not touch `src/hongstr/**`.
- It does not sync raw/state/cache/db artifacts.
- It never deletes files on iCloud target.
- Any failure is logged as `WARN` and returns exit code `0`.
- It is a knowledge-layer publish surface only and must not be treated as SSOT for `/status`, `/daily`, or `/dashboard`.

## Source and target

Defaults:

- `OBSIDIAN_PRIMARY_ROOT`: `<repo_root>/_local/obsidian_vault`
- `ICLOUD_OBSIDIAN_ROOT`: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian`
- `ICLOUD_VAULT_NAME`: `HONGSTR_MIRROR`
- `MIRROR_ENABLED`: `1`

Resolved vaults:

- Source vault: `${OBSIDIAN_PRIMARY_ROOT}/HONGSTR` (or `${OBSIDIAN_PRIMARY_ROOT}` if it is already `.../HONGSTR`)
- Target vault: `${ICLOUD_OBSIDIAN_ROOT}/${ICLOUD_VAULT_NAME}`

Operational note:

- The source vault and iCloud mirror target are intentionally different paths.
- Typical source vault: `/Users/hong/Projects/HONGSTR/_local/obsidian_vault/HONGSTR`
- Typical iCloud target: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/HONGSTR_MIRROR`
- Opening the source vault in Obsidian does not mean the iCloud mirror target is the currently opened vault.

Active publish contract (single-direction publish):

- `HONGSTR/Dashboards/**`
- `HONGSTR/Daily/**`
- `HONGSTR/KB/_meta/**`
- `HONGSTR/KB/PR/**`
- `HONGSTR/KB/Runbooks/**`
- `HONGSTR/KB/Incidents/**`
- `HONGSTR/KB/Research-Summaries/**`

Current Daily contract:

- Active daily notes are published under `Daily/YYYY/MM/YYYY-MM-DD.md`.

Legacy / non-current contract:

- `KB/SSOT/**` is frozen legacy content and is excluded from active mirror refresh.
- `KB/SSOT/Daily/**` is not the active daily publish contract and must not be used as the current daily mirror surface.
- Because delete mode is disabled, old `KB/SSOT/**` files may still remain on the iCloud target until an operator removes them manually. Treat them as stale carry-over only.

Optional future surface (disabled by default):

- `State-Refs/**` or `Snapshots/**` may be added only as readable pointers or short summaries to canonical `data/state/*.json`.
- They must not mirror full canonical JSON, must not be named as SSOT, and must not become a dependency for `/status`, `/daily`, or `/dashboard`.
- They are not part of the current active publish contract.

Current excludes:

- `.obsidian/workspace*`
- `.obsidian/cache`
- `.obsidian/*history*`
- `raw/`
- `state/`
- `cache/`
- `db/`
- `*.parquet`, `*.pkl`, `*.pickle`, `*.joblib`

## launchd schedule

- Label: `com.hongstr.obsidian_mirror`
- Daily local time: `08:10`
- Template: `launchd/com.hongstr.obsidian_mirror.plist`
- Runtime plist: `~/Library/LaunchAgents/com.hongstr.obsidian_mirror.plist`
- Logs:
  - `_local/logs/launchd_obsidian_mirror.out.log`
  - `_local/logs/launchd_obsidian_mirror.err.log`

## Install and operations

```bash
bash scripts/install_obsidian_mirror_launchd.sh install
bash scripts/install_obsidian_mirror_launchd.sh status
bash scripts/install_obsidian_mirror_launchd.sh reload
bash scripts/install_obsidian_mirror_launchd.sh uninstall
```

Manual one-shot run:

```bash
bash scripts/obsidian_mirror_run.sh
```

## Kill switch

Temporary one-shot disable:

```bash
MIRROR_ENABLED=0 bash scripts/obsidian_mirror_publish.sh
```

Skip dashboards export while keeping mirror run:

```bash
DASHBOARDS_EXPORT_ENABLED=0 bash scripts/obsidian_mirror_run.sh
```

Disable launchd runtime:

```bash
launchctl setenv MIRROR_ENABLED 0
launchctl kickstart -k gui/$(id -u)/com.hongstr.obsidian_mirror
```

Re-enable launchd runtime:

```bash
launchctl setenv MIRROR_ENABLED 1
launchctl kickstart -k gui/$(id -u)/com.hongstr.obsidian_mirror
```

## DoD

- Mirror script can run repeatedly without deleting iCloud files.
- Missing source folder, missing iCloud path, or rsync error produces `WARN` and process exit code remains `0`.
- Active publish contract and excludes are enforced.
- Daily note publishing is verified under `HONGSTR_MIRROR/Daily/YYYY/MM/YYYY-MM-DD.md`.
- `KB/SSOT/**` is documented as frozen legacy / non-current and excluded from active refresh.
- 7-day operational verification is completed by operator using launchd logs.

## Troubleshooting

### iCloud path does not exist

Symptoms:

- `WARN ... target_vault_not_accessible`

Actions:

1. Ensure iCloud Drive and Obsidian iCloud sync are enabled on macOS.
2. Confirm the path exists:

```bash
ls -la ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/Obsidian
```

3. Re-run:

```bash
bash scripts/obsidian_mirror_publish.sh
```

### Primary vault path does not exist

Symptoms:

- `WARN ... primary_vault_not_found`

Actions:

1. Confirm source path:

```bash
ls -la _local/obsidian_vault/HONGSTR
```

2. Or set explicit path:

```bash
OBSIDIAN_PRIMARY_ROOT="/abs/path/to/obsidian_vault" bash scripts/obsidian_mirror_publish.sh
```

### Lock already exists

Symptoms:

- `WARN ... lock_exists`

Actions:

1. Check if another run is active.
2. If stale lock is confirmed, remove and rerun:

```bash
rm -rf /tmp/com.hongstr.obsidian_mirror.lock
bash scripts/obsidian_mirror_publish.sh
```

### iCloud sync delay

Symptoms:

- Script reports `INFO ... synced`, but files appear later on iCloud.

Actions:

1. Wait for iCloud background sync.
2. Keep launchd schedule active.
3. Verify next run logs:

```bash
tail -n 80 _local/logs/launchd_obsidian_mirror.out.log
tail -n 80 _local/logs/launchd_obsidian_mirror.err.log
```

### Verify current Daily note is mirrored

Source note:

```bash
ls -la _local/obsidian_vault/HONGSTR/Daily/$(date +%Y)/$(date +%m)/$(date +%F).md
```

Target note:

```bash
ls -la ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/Obsidian/HONGSTR_MIRROR/Daily/$(date +%Y)/$(date +%m)/$(date +%F).md
```

### Verify active KB / Dashboards surfaces are mirrored

KB PR note:

```bash
ls -la _local/obsidian_vault/HONGSTR/KB/PR/2026
ls -la ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/Obsidian/HONGSTR_MIRROR/KB/PR/2026
```

Dashboard note:

```bash
ls -la _local/obsidian_vault/HONGSTR/Dashboards
ls -la ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/Obsidian/HONGSTR_MIRROR/Dashboards
```

Verification rules:

1. `KB/_meta/`, `KB/PR/`, `KB/Runbooks/`, `KB/Incidents/`, `KB/Research-Summaries/`, `Dashboards/`, and `Daily/` may be present in the mirror target.
2. `KB/SSOT/**` is legacy; if it still appears on target, treat it as frozen carry-over, not active output.
3. Missing target files degrade to `WARN` only; they do not change canonical SSOT state.
4. Canonical truth remains under `data/state/*.json`; mirror content is for publish/knowledge convenience only.

### Legacy broken job

- `com.hongstr.obsidian_daily` is a legacy/broken runtime path that points to a missing script and is not part of the current mirror contract.
- Keep it disabled or removed from the local launchd runtime; do not use it as the producer for current `Daily/YYYY/MM` notes.
