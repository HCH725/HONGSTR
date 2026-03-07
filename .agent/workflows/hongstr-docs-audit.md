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

- If the text in the document suggests a necessary change in the actual core engine (`src/hongstr/**`) or runtime scripts (`scripts/refresh_state.sh`).
- Output the `hongstr-handoff-to-codex.md` note and do not apply code changes.
