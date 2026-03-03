---
name: hongstr-plan-only
description: Default to planning mode. Propose steps + commands, but do not modify files unless explicitly approved.
compatibility: opencode
---

## Rules
- Assume **no-write** by default: do not edit/create files unless the user explicitly says "apply" / "make the change".
- If a request could touch SSOT writers/state producers (`scripts/refresh_state.sh`, `scripts/state_snapshots.py`, `reports/state_atomic/*`), STOP and ask for confirmation.
- Prefer small, reversible changes and minimal diffs.

## Required output format
1) Plan (1–5 bullets)
2) Commands (copy-paste)
3) What to paste back (exact outputs)
