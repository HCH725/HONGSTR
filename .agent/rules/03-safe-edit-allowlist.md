---
description: Safe Edit Allowlist for Antigravity Sandbox
---

# Safe Edit Allowlist

You are a bounded auxiliary agent. You may ONLY modify files that fall within the specified "Allowed" directories or file types.

## Allowed (Safe to Edit)

- `docs/**` (governance, reports, templates)
- `.agent/**` (rules, workflows, prompts)
- `AGENTS.md` (agent descriptions)
- Any non-core governance checklists or Markdown documentation.
- Necessary non-core tests or docs tooling (only if explicitly requested and safe).

## Prohibited (HARD STOP)

If you attempt to modify any of these paths, immediately STOP and hand off to Codex.

- `src/hongstr/**` (The Core Engine)
- ANY state or producer semantics.
- ETL, backfill, or any execution critical path.
- `tg_cp` (Telegram Control Plane) authority or display boundaries.
- `.env` files or any secrets/keys loading mechanism.

## Rule of Thumb

If you are unsure if a file is safe, assume it is **PROHIBITED**.
