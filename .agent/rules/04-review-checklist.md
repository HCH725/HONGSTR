---
description: Read-Only Governance & Review Checklist
---

# Review Checklist

When performing code reviews, PR audits, or evaluating new changes, verify the following points.

## 1. No Core Path Touched

- Are there any modifications to `src/hongstr/**`?
- **If YES -> FAIL**

## 2. No Secrets / Env Behavior Changed

- Are there any changes to how `.env` works, new required secrets, or potential leaks?
- **If YES -> FAIL**

## 3. No SSOT Writer Boundary Crossed

- Does this change introduce a new writer for a canonical state file without being registered in the Writer Inventory?
- Is an unapproved script modifying files owned by `refresh_state.sh` or `state_snapshots.py`?
- **If YES -> FAIL**

## 4. No Consumer-Side Recomputation

- Does a consumer (like `tg_cp` or a Dashboard) attempt to calculate state, health, or indicators that should be read from a state file?
- **If YES -> FAIL**

## 5. Governance & Policy Alignment

- Does this `.agent/**` rule/workflow conflict with `AGENTS.md` or existing governance docs?
- Does it create a duplicate policy source or second truth?
- **If YES -> WARN or FAIL, and stop for alignment.**
- Does the PR align with the specified Canonical Health Pack structure?
- Is it correctly categorized in the Stage Registry?
- If the change is broad or ambiguous, **STOP and hand off to Codex**.
