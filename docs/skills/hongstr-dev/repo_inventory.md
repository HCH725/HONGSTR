# Repo Inventory (Dev)

**MUST READ FIRST:** `docs/skills/global_red_lines.md`

## Core (DO NOT CHANGE)
- `src/hongstr/**` (core semantics must remain diff=0)

## Control plane / Telegram (read-only)
- `_local/telegram_cp/` (tg_cp read-only broker; no exec)

## State producers (runtime snapshots; do not commit outputs)
- `scripts/state_snapshots.py`
- `scripts/refresh_state.sh`
- Output: `data/state/*.json` (untracked)

## Ops scripts (scheduling / runbooks)
- `scripts/gh_pr_merge.sh` (Plan B PR creation + auto-merge)
- launchd plists under `~/Library/LaunchAgents/` (local machine)

## Docs / SOP
- `docs/` (inventory, brakes, ops_local, etc.)
