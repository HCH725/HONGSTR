---
date: YYYY-MM-DD
ssot_ts_utc: ""
linked_pr: "#NNN"
linked_issue: "#NNN"
status: proposed   # proposed | accepted | deprecated | superseded
superseded_by: ""  # fill if deprecated
---

# Decision: <topic>

> ADR-lite: one decision, one note. Keep it short and linkable.

## Status

**{{ status }}** — {{ date }}

## Context
<!-- What problem or tension led to this decision?
     Include concrete data or examples where possible. -->

## Decision
<!-- The actual choice made. Be specific. -->

## Rationale
<!-- Why this option over alternatives?
     List at least two alternatives considered. -->

### Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| | |
| | |

## Consequences

- **Positive:** What gets better?
- **Negative / Trade-offs:** What gets worse or more constrained?
- **Neutral / Operational:** What changes in day-to-day ops?

## Review Trigger
<!-- When should this decision be revisited? (time-based, metric-based, event-based) -->
Example: "Revisit if OOS Sharpe drops below 1.0 for two consecutive weeks."

## References

- Linked PR: {{ linked_pr }}
- Linked Issue: {{ linked_issue }}
- SSOT: `data/state/` at `{{ ssot_ts_utc }}`
