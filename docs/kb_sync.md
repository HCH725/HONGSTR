# KB Sync – GitHub PR → Obsidian KB Notes

> **TL;DR** Every hour, poll merged PRs from GitHub and write human-readable notes to your local Obsidian vault.  
> KB files are **private** and never committed to git. LanceDB indexing is handled automatically by the existing `com.hongstr.obsidian_rag` agent.

---

## Overview

`com.hongstr.kb_sync` runs `scripts/kb_sync_run.sh` → `scripts/kb_sync_github_prs.py` once per hour.

For each newly merged PR (base=main, merged_at > cursor):

1. Fetches PR metadata + file list via **GitHub API** (not `gh` CLI).
2. Writes `_local/obsidian_vault/HONGSTR/KB/PR/YYYY/PR-####.md`.
3. Advances the cursor to the highest `merged_at` of successfully written notes.

**What it does NOT do:**

- Does **not** commit anything to git (`_local/` is gitignored).
- Does **not** run LanceDB indexing (`com.hongstr.obsidian_rag` handles that on its own hourly cycle).
- Does **not** place orders or touch trading state.

---

## Prerequisites

### GitHub Token

Export a **read-only** Personal Access Token with `repo` (classic) or `contents: read` (fine-grained) scope:

```bash
# In your shell profile or .env (already gitignored):
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
```

The script reads `GITHUB_TOKEN` or `GH_TOKEN`. If neither is set it exits with `FAIL`.

> **Fine-grained PAT minimum permissions:** Repository → Contents: Read-only

---

## Install / Start

```bash
# From repo root:
bash scripts/install_kb_sync_launchd.sh
```

This will:

1. Render `launchd/com.hongstr.kb_sync.plist` → `~/Library/LaunchAgents/com.hongstr.kb_sync.plist`
2. Validate plist syntax (`plutil -lint`)
3. Unload any previous version
4. Bootstrap + kickstart the job immediately
5. Print `launchctl print` status
6. Tail last 80 lines of both logs

> **Requirement:** `GITHUB_TOKEN` must be present in your environment or in `repo_root/.env` at run time.

---

## Manual Run

```bash
# Single on-demand run (uses .venv python, inherits env):
bash scripts/kb_sync_run.sh

# Dry-run (no files written, no cursor advance):
.venv/bin/python scripts/kb_sync_github_prs.py --dry-run
```

---

## Stop / Disable

```bash
# Temporarily stop the running job:
launchctl bootout "gui/$(id -u)/com.hongstr.kb_sync"
```

---

## Uninstall

```bash
# Stop and remove the agent:
launchctl bootout "gui/$(id -u)/com.hongstr.kb_sync" 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.hongstr.kb_sync.plist
```

---

## Logs

| Log file | Content |
| --- | --- |
| `~/Library/Logs/hongstr/kb_sync.out.log` | stdout: OK/WARN/FAIL summary + JSON result |
| `~/Library/Logs/hongstr/kb_sync.err.log` | stderr: warnings, rate-limit messages, errors |

```bash
# Live tail:
tail -f ~/Library/Logs/hongstr/kb_sync.out.log

# Last 80 lines of each:
tail -n 80 ~/Library/Logs/hongstr/kb_sync.out.log
tail -n 80 ~/Library/Logs/hongstr/kb_sync.err.log
```

---

## Cursor / State

```text
_local/obsidian_vault/HONGSTR/_meta/kb_sync_state.json
_local/obsidian_vault/HONGSTR/KB/_meta/kb_sync_state.json
```

`kb_sync_github_prs.py` writes both files each run so users can check either location.
If only one file exists, the sync job reads from the first available state file.

| Field | Description |
| --- | --- |
| `last_merged_at_utc` | Highest `merged_at` of successfully written PR notes |
| `last_run_utc` | UTC timestamp of last run attempt |
| `last_status` | `OK`, `WARN`, or `FAIL` |
| `last_error` | Last warning or error message (if any) |

To **reset** the cursor (re-sync all recent PRs):

```bash
rm -f _local/obsidian_vault/HONGSTR/_meta/kb_sync_state.json
rm -f _local/obsidian_vault/HONGSTR/KB/_meta/kb_sync_state.json
```

> ⚠️ After reset, the first run will attempt to backfill up to **50 PRs**. Run again to continue backfilling older PRs.

---

## Troubleshooting

### Rate Limit (403 / 429)

The poller hits GitHub's secondary rate limit.

- Status logged as `WARN`; cursor is **not** advanced.
- Will automatically retry on next hourly run.
- If persistent: reduce `--limit` (default 50) or wait for rate limit window to reset.

### Token Permission Error (401 / 403 on first request)

- Verify token has `repo` (classic) or `contents: read` (fine-grained) scope.
- Check `GITHUB_TOKEN` is exported in the environment where the launchd job runs.
- The `.env` file in repo root is sourced automatically by `kb_sync_run.sh`.

### First-Run Backfill Is Slow

- Default cap is **50 PRs per run**. If there are hundreds of historical PRs, run manually multiple times:

  ```bash
  bash scripts/kb_sync_run.sh   # repeat until no new "written" count
  ```

- Or raise the limit for a one-off run:

  ```bash
  .venv/bin/python scripts/kb_sync_github_prs.py --limit 200
  ```

### Job Shows "Last exit code ≠ 0"

```bash
launchctl print "gui/$(id -u)/com.hongstr.kb_sync"
tail -n 80 ~/Library/Logs/hongstr/kb_sync.err.log
```

Common causes: missing `GITHUB_TOKEN`, Python not found, or vault directory permission issues.

---

## Architecture Notes

- **KB vault is private:** All notes stay in `_local/` which is gitignored (`_local/` in `.gitignore`).
- **Indexing is handled separately:** `com.hongstr.obsidian_rag` runs on its own hourly cycle and indexes the entire vault (including the new `KB/PR/` notes) into LanceDB. No changes to that agent are needed.
- **No LLM used:** Note summaries are extracted using simple text rules (no AI calls).
- **No core diffs:** `src/hongstr/**` is untouched.
