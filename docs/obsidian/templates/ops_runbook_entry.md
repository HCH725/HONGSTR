---
date: YYYY-MM-DD
ssot_ts_utc: ""
linked_pr: "#NNN"
linked_issue: "#NNN"
status: draft   # draft | active | deprecated
owner: ""
---

# Runbook: <topic>

## Purpose
<!-- When should an operator reach for this runbook? One sentence. -->

## Trigger / Context
<!-- What condition or alert causes someone to run this? -->

## Prerequisites

- [ ] Access to: `bash scripts/guardrail_check.sh`
- [ ] Access to SSOT reads: `data/state/`
- [ ] (add others)

## Steps

```bash
# Step 1: Verify current state
bash scripts/guardrail_check.sh
```

1. **Check:** Describe what to check first.
2. **Diagnose:** How to narrow down the problem.
3. **Act:** Exact commands to run (**read-only** unless explicitly stated).
4. **Verify:** How to confirm the fix worked.

## Rollback

```bash
git revert <sha>
git push
gh pr create --title "revert: ..." --body "Rollback for incident YYYY-MM-DD"
```

## Related Notes

- See incident: `Incidents/YYYY-MM-DD_<slug>.md`
- See decision: `Decisions/YYYY-MM-DD_<topic>.md`

## References

- Linked PR: {{ linked_pr }}
- Linked Issue: {{ linked_issue }}
