---
date: YYYY-MM-DD
ssot_ts_utc: ""
linked_pr: "#NNN"
linked_issue: "#NNN"
status: draft
severity: P1   # P1 (trading impact) | P2 (data gap) | P3 (ops noise)
---

# Incident Postmortem: <slug>

## Summary
<!-- One-paragraph executive summary of what happened and the impact. -->

## Timeline

| UTC Time | Event |
|----------|-------|
| HH:MM | Detection: |
| HH:MM | Triage: |
| HH:MM | Mitigation: |
| HH:MM | Resolution: |

## Root Cause
<!-- Specific, verifiable root cause. Avoid vague descriptions. -->

## Impact

- **Trading impact:** none / reduced / halted
- **Data impact:** affected symbols/timeframes
- **Duration:** X hours

## Detection

- How was this detected? (alert / manual / monitoring gap?)
- Was there a lagging indicator that should be promoted?

## Mitigation Steps Taken

1.
2.

## Corrective Actions

| Action | Owner | Target Date | PR/Issue |
|--------|-------|-------------|----------|
| | | | |

## Lessons Learned
<!-- What should change in process, monitoring, or code? -->

## References

- SSOT snapshot: `data/state/system_health_latest.json` at `{{ ssot_ts_utc }}`
- Linked PR: {{ linked_pr }}
- Linked Issue: {{ linked_issue }}
