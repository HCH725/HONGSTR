---
description: HONGSTR Read-Only GitHub PR Review Workflow
---

# HONGSTR Read-Only GitHub PR Review Workflow

**Use Case:**
Auditing and reviewing Pull Requests against the established HONGSTR Red Lines and Stage Registry boundaries.

**Allowed Scope:**

- Reading GitHub PR descriptions and diffs.
- Identifying missing checklist elements or governance risks (e.g. `is_usable=false` logic put in the wrong layer).
- Producing a review checklist report.
- NO core code modifications.

**Workflow Steps:**

1. Fetch PR details using the GitHub CLI (`gh`).
2. Read the PR diff, focusing on changed files.
3. Apply `04-review-checklist.md` rules.
4. Output the validation results in a structured format:
   - Card boundary risks
   - Premature DONE risks
   - PM Blockers

**Output Format:**
A short review report format, generally prefixed with the objective (e.g. "Stage 1 Merge Guard Report").

**When to Stop:**

- After delivering the exact requested audit report to the user.

**When to Upgrade to Codex:**

- If the PR needs significant core code refactoring to pass the audit, state exactly what must be corrected and output the `hongstr-handoff-to-codex.md` note.
