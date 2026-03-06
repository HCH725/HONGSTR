# Obsidian iCloud Mirror Publisher

## Overview

`com.hongstr.obsidian_mirror` runs `scripts/obsidian_mirror_run.sh` once per day and performs an export-then-mirror chain to iCloud Obsidian vault `HONGSTR_MIRROR`.

Current launchd chain uses `scripts/obsidian_mirror_run.sh`:

1. Export dashboards from SSOT: `scripts/obsidian_dashboards_export.sh`
2. Publish mirror to iCloud: `scripts/obsidian_mirror_publish.sh`

This mirror is governance-only and non-blocking:

- It does not touch `src/hongstr/**`.
- It does not sync raw/state/cache/db artifacts.
- It never deletes files on iCloud target.
- Any failure is logged as `WARN` and returns exit code `0`.

## Source and target

Defaults:

- `OBSIDIAN_PRIMARY_ROOT`: `<repo_root>/_local/obsidian_vault`
- `ICLOUD_OBSIDIAN_ROOT`: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian`
- `ICLOUD_VAULT_NAME`: `HONGSTR_MIRROR`
- `MIRROR_ENABLED`: `1`
- `STRICT_MIRROR`: `0`
- `DRY_RUN`: `0`
- `OBSIDIAN_MIRROR_LOCK_DIR`: `/tmp/com.hongstr.obsidian_mirror.lock`

Resolved vaults:

- Source vault: `${OBSIDIAN_PRIMARY_ROOT}/HONGSTR` (or `${OBSIDIAN_PRIMARY_ROOT}` if it is already `.../HONGSTR`)
- Target vault: `${ICLOUD_OBSIDIAN_ROOT}/${ICLOUD_VAULT_NAME}`

Current whitelist (single-direction publish):

- `HONGSTR/KB/**`
- `HONGSTR/Dashboards/**`

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

## Strict Mirror (manual repair mode)

`STRICT_MIRROR=1` enables delete sync and makes mirror target exactly match Primary for included paths.

`DRY_RUN=1` prints the plan without changing files.

Run dry-run first:

```bash
cd /Users/hong/Projects/HONGSTR
DRY_RUN=1 STRICT_MIRROR=1 bash scripts/obsidian_mirror_publish.sh
```

Apply strict repair:

```bash
cd /Users/hong/Projects/HONGSTR
STRICT_MIRROR=1 bash scripts/obsidian_mirror_publish.sh
```

SOP:

1. Run dry-run and review files listed by rsync itemized output.
2. Confirm scope is only `KB/` and `Dashboards/`.
3. Run strict repair.
4. Validate mirror notes on iCloud Obsidian vault.

Notes:

- Default launchd schedule remains safe mode with delete disabled.
- Strict mode is manual-only and should be used for mirror repair.

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
- Whitelist and excludes are enforced.
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
