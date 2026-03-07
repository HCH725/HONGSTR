---
description: HONGSTR Handoff to Codex Workflow
---

# HONGSTR Handoff to Codex Workflow

**Use Case:**
Used when a task steps beyond the bounded auxiliary agent's capabilities or permissions. This is the fallback safety mechanism for HONGSTR tasks.

**Allowed Scope:**

- Generate a summary note for the user to hand off to Codex.
- NO code modification.

**Workflow Steps:**
When encountering a requirement that touches:

- `src/hongstr/**`
- Any `refresh_state` / `state_snapshots` core script logic.
- `.env` structures.
- Launchd/Orchestration runtimes.
- Or any other item outside the `03-safe-edit-allowlist.md`.

You MUST:

1. Immediately cease all attempts to write or alter files.
2. Output a handoff block summarizing the context.

**Output Format:**
Provide the following markdown block to the user:

```markdown
# ⚠️ HONGSTR Core Boundary Reached: Codex Handoff Note

I am unable to proceed with this task, as it violates the HONGSTR read-only/docs-first boundaries for Antigravity. Please hand this context over to **Codex**:

**Task Summary:** [Briefly describe the overall objective]
**Exact Boundary Crossed:** [e.g. Attempted to modify src/hongstr/engine/matcher.py or rewrite state semantics]
**Impacted File Paths:** [List the specific files that need modification]
**Why Antigravity is Stopping:** [Explicit rule reference, e.g. Rule 00 - Core Engine]
**Evidence Already Collected:** [List what you have analyzed or discovered so far]
**Proposed Acceptance Evidence:** [What should Codex produce to prove this is done?]
**Recommended Next Step:** [What Codex should do first]
```

**When to Stop:**

- Stop immediately after outputting this note.
