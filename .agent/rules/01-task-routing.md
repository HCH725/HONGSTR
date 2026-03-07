---
description: Task Routing and Scope Assessment
---

# Task Routing

Before beginning execution on any task, you must evaluate the task scope and routing category.

## Sandbox First Principle

If a task is **not** explicitly part of the current mainline HONGSTR checklist or roadmap, it MUST be treated as a "Sandbox" task.

## Assessment Checklist

1. **Is this on the mainline checklist?**
   - If NO -> Tag as Sandbox/Provisional.
2. **Does this touch the core path?**
   - If YES -> Stop and hand off to Codex.
3. **Does this involve `.env` or secrets?**
   - If YES -> Stop and hand off to Codex.
4. **Is this a large refactor or complex logic change?**
   - If YES -> Stop and hand off to Codex.

## Allowed Routing

You are only authorized to proceed if the task is routed as:

- Docs updates (`docs/**`)
- Governance / Process alignment
- Sandbox `.agent` rules/workflows updates
- Read-only code review or audit support

If the task falls outside these allowed routes, utilize the `hongstr-handoff-to-codex` workflow.
