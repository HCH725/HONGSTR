---
description: HONGSTR Docs Audit Workflow
---

# HONGSTR Docs Audit Workflow

**Use Case:**
Auditing existing markdown documents, reports, and governance specs against the latest HONGSTR Stage Registry or PR outputs.

**Allowed Scope:**

- Reading and writing `docs/**`
- Reading `.agent/rules/`
- Reading PRs and issues via Linear or GitHub CLI
- Read-only GitHub / Linear inspection is allowed.
- Create/update Linear tracking is allowed only for sandbox/governance tracking. This does NOT authorize core code changes.
- NO core code modifications.

**Workflow Steps:**

1. Retrieve the latest rules from `.agent/rules/`.
2. Retrieve the target document from `docs/`.
3. Compare the document against the latest policies (e.g. Stage Registry, SSOT definition).
4. Outline inconsistencies.
5. Apply fixes to the document in `docs/` ONLY.

**Output Format:**

- Modify the document.
- Generate a PR using the `02-pr-output-contract.md` structure.

**When to Stop:**

- Stop when the specified document has been corrected.

**When to Upgrade to Codex:**

- If document findings imply core engine / producer / runtime / `.env` / control-plane authority changes, stop and output `hongstr-handoff-to-codex.md`.
