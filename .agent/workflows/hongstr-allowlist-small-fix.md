---
description: HONGSTR Allowlist Small Fix Workflow
---

# HONGSTR Allowlist Small Fix Workflow

**Use Case:**
Executing minor fixes or documentation updates that strictly reside within the "Safe Edit Allowlist". Examples include updating markdown documentation formatting, moving a stage tracker checklist item, or editing a prompt file in `.agent`.

**Allowed Scope:**

- ONLY files documented in `.agent/rules/03-safe-edit-allowlist.md`.
- Read and write access to `docs/**`, `AGENTS.md`, and `.agent/**`.
- GitHub branch, commit, push, and PR creation (see `05-governance-actions-allowed.md`).
- **CRITICAL**: GitHub/Linear bounded collaboration is allowed, but this does NOT authorize edits to core code (`src/hongstr/**`), `.env`, producer/state semantics, ETL/backfill, or `tg_cp` boundaries.

**Workflow Steps:**

1. Confirm the target file is in the safe allowlist.
2. If NOT, ABORT and output `hongstr-handoff-to-codex.md`.
3. If YES, implement the small fix or formatting change.
4. Execute the bounded delivery: `git checkout -b`, `git commit`, `git push`.
5. Always open a PR containing the PR Output Contract (`02-pr-output-contract.md`) via Google/GitHub tooling.

**Output Format:**

- Create a PR containing the exact changes.
- Do NOT auto-merge.

**When to Stop:**

- Stop after creating the PR, linking the Linear card if available, and waiting for user review.

**When to Upgrade to Codex:**

You MUST route the task to Codex (using `hongstr-handoff-to-codex.md`) and stop immediately if the issue:

- Touches `src/hongstr/**`
- Touches producer / state semantics / SSOT writer boundary
- Touches control plane authority / `tg_cp` boundary
- Touches `.env` / secrets / config loading behavior
- Requires deploy / rollback / runtime verification
- Is an ambiguous request crossing multiple boundaries
- Requires a large refactor or complex logic change
