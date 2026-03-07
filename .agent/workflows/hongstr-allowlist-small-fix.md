---
description: HONGSTR Allowlist Small Fix Workflow
---

# HONGSTR Allowlist Small Fix Workflow

**Use Case:**
Executing minor fixes or documentation updates that strictly reside within the "Safe Edit Allowlist". Examples include updating markdown documentation formatting, moving a stage tracker checklist item, or editing a prompt file in `.agent`.

**Allowed Scope:**

- ONLY files documented in `.agent/rules/03-safe-edit-allowlist.md`.
- Read and write access to `docs/**`, `AGENTS.md`, and `.agent/**`.

**Workflow Steps:**

1. Confirm the target file is in the safe allowlist.
2. If NOT, ABORT and output `hongstr-handoff-to-codex.md`.
3. If YES, implement the small fix or formatting change.
4. Always open a PR containing the PR Output Contract (`02-pr-output-contract.md`).

**Output Format:**

- Create a PR containing the exact changes.
- Do NOT auto-merge.

**When to Stop:**

- Stop after creating the PR, linking the Linear card if available, and waiting for user review.

**When to Upgrade to Codex:**

- If applying the change requires altering scripts, python configurations, environmental variables, or execution logic.
