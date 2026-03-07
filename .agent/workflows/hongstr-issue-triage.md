---
description: HONGSTR Issue Triage Workflow
---

# HONGSTR Issue Triage Workflow

**Use Case:**
Evaluating a new Linear issue, aligning it with the Master Overview (HONG-15), and determining its stage or if it's a Sandbox request.

**Allowed Scope:**

- Reading Linear issues
- Querying GitHub status
- Categorizing issue text and mapping to Stage Registry keys.
- **NEW**: Creating or updating Linear tracking issues to assign sandbox/provisional status (see `05-governance-actions-allowed.md`).
- NO core code modifications.

**Workflow Steps:**

1. Fetch issue details from Linear.
2. Determine if the issue falls under P0-P9 boundaries.
3. Check `01-task-routing.md` to determine if it is "Mainline" or "Sandbox".
4. Determine if it attempts to break the SSOT boundaries, Core Engine, or Control Plane restrictions.
5. Create or update the Linear tracking item with the triage result.
   - *Note: Sandbox triage can create/update Linear tracking, but this DOES NOT authorize modifying core logic, `.env`, or state semantics.*

**Output Format:**
A short Triage Report containing:

- Alignment (Mainline Px / Sandbox)
- Risk level (e.g. touches_P0_deterministic, touches_ssot_writer_boundary)
- Drift warnings

**When to Stop:**

- Stop after providing the Triage Report to the user.

**When to Upgrade to Codex:**
You MUST route the task to Codex (using `hongstr-handoff-to-codex.md`) and stop immediately if the issue:

- Touches `src/hongstr/**`
- Touches producer / state semantics / SSOT writer boundary
- Touches control plane authority / `tg_cp` boundary
- Touches `.env` / secrets / config loading behavior
- Requires deploy / rollback / runtime verification
- Is an ambiguous request crossing multiple boundaries
- Requires a large refactor or complex logic change
