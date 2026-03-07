---
description: Pull Request Output Contract
---

# PR Output Contract

Whenever you generate a Pull Request, the PR description MUST follow this exact structure to ensure governance compliance.

## Required Structure

```markdown
## Stage / checklist alignment
- [State whether this is part of Stage 1/2/3 mainline, or Sandbox if not on checklist]
- Phase: [Phase Name]
- Checklist Item: [Item ID or "Sandbox / Not in checklist"]

## Evidence
- [List specific merged PRs, commits, or canonical paths that act as evidence. If this PR IS the evidence, state the files changed.]
- Canonical paths: [e.g., docs/ops_data_plane.md, .agent/rules/00-hongstr-core-boundaries.md]

## Degrade
- [What happens if this PR fails or is reverted? e.g., Fall back to manual documentation]

## Kill switch
- [Explicit steps: e.g. "Stop immediately. Do not add further commits. Preserve this branch for human review. If PR is open, close/revert. Output hongstr-handoff-to-codex note."]
- Trigger conditions: [e.g. If it touches src/hongstr/** or breaks the SSOT writer boundary]

## Legacy Impact
- [For governance/.agent/** PRs: Does this conflict with AGENTS.md or existing docs? Does it create a second truth?]
- [Removal/Rollback Plan: How to cleanly revert this if it causes friction?]
- [For code: Impacts on older configs or workflows (often N/A for sandbox)]
```

## Additional PR Rules

- **Never Auto-Merge**: Always wait for human review.
- **Clear Labeling**: The PR body MUST clearly state if it is a "sandbox / docs-first / no core diff" change.
