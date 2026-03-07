# HONGSTR Agent Rules

This file is the operational entrypoint for coding agents working in HONGSTR. It aligns task intake, red lines, evidence, and PR language so governance stays reviewable and small in scope.

## 1. Task intake is mandatory

Before changing files, every task must declare:

```md
Stage:
Checklist item:
Plane:
DoD improved:
Allowed paths:
Forbidden paths:
Evidence:
Degrade:
Kill switch / rollback:
Legacy Impact: Keep / Merge / Kill / Removal plan
```

If the task cannot be mapped to a Stage and Checklist item, label it:

```md
NOT IN CHECKLIST -> SANDBOX FIRST
```

Keep scope isolated until a reviewer approves a broader slice.

## 2. Linear-first governance (required)

For HONGSTR, any initiated task must be tracked in Linear before formal execution.

This applies to:

- mainline work
- sandbox work
- docs / scripts / governance / research / review tasks
- external adoption / evaluation tasks
- any work that requires execution, tracking, validation, or closure

Rules:

1. Initiate -> Register in Linear -> Execute -> Track -> Close
2. No Linear entry = no formal execution
3. Sandbox also requires tracking
4. Do not leave orphan work
5. Every item must end with a closure outcome:
   - `DONE`
   - `REJECT`
   - `DEFERRED`
   - `SANDBOX ONLY`
   - `MERGED / SUPERSEDED`

If a task cannot be mapped to an existing mainline item:

- register it in Linear as sandbox/candidate first

If Linear tracking is missing:

- stop
- classify the task
- propose the matching Linear item
- do not continue into implementation

Executor reinforcement:

- For `Codex`: Before executing any non-trivial HONGSTR task, verify that a matching Linear issue exists. If none exists, stop and treat the task as intake first.
- For `antigravity`: Do not begin formal execution unless there is already a matching Linear tracking item. Sandbox work also requires Linear tracking.

## 3. Non-negotiable red lines

- `src/hongstr/**` is `core-path protected`.
- Do not break the SSOT writer boundary. Canonical publication of `data/state/*` belongs to the State Plane writer path only.
- `/status`, `/daily`, and `/dashboard` must remain `SSOT-only`.
- `/status`, `/daily`, and `/refresh_state` must remain deterministic and must not depend on live external APIs for top-level output.
- Missing or unreadable SSOT input must degrade deterministically to `UNKNOWN` plus `refresh_hint`.
- Control Plane is read-only. Telegram, Dashboard, and CLI must not perform second-pass recomputation of top-level state and must not write canonical state.
- Research / ML is always `report-only` and must remain pausable.
- Secrets, `data/**` artifacts, `_local/**` artifacts, runtime outputs, caches, `*.parquet`, `*.pkl`, and similar generated files must not enter git.
- No opportunistic refactor. No while-here edits. Smallest possible PR only.
- Any request that breaks these red lines must stop and be escalated before work continues.

## 4. Plane guardrails

- State Plane owns the canonical SSOT writer boundary.
- Data Plane may produce raw or derived inputs, but it must not publish competing canonical truth for control-plane status.
- Control Plane is read-only against canonical SSOT surfaces.
- Telegram, Dashboard, and CLI must consume top-level status from SSOT rather than recomputing it.
- Research Plane may emit reports and evidence only. It must not back-write runtime truth.

## 5. Path discipline

- Respect task-specific `Allowed paths` and `Forbidden paths` before making edits.
- If a file is outside `Allowed paths`, treat it as out of scope unless the task is re-scoped explicitly.
- Medium or large changes must always include `Legacy Impact: Keep / Merge / Kill / Removal plan`.
- Small changes should still state legacy impact explicitly, even if the answer is `Keep`.

## 6. Evidence chain and delivery discipline

- Every task must produce a clear evidence chain before completion.
- Default completion preflight is:
  - guardrail check
  - schema validation
  - local smoke test
- If a preflight item is not applicable, say `N/A` and explain why in the task evidence or PR body.
- PRs must use the same governance fields declared at task intake.
- `Expected SSOT/output impact` must state either `none` or the exact consumer-facing effect.
- `Out of scope / not changed` must explicitly call out protected paths or behaviors that were left untouched.

## 7. PR sizing

- Prefer the smallest reviewable change that closes a single checklist item.
- Do not mix docs/governance work with runtime logic changes.
- Do not fix nearby issues unless they are required to satisfy the declared checklist item and stay within allowed paths.

## 8. Agent routing

- `Codex` owns high-complexity, multi-file, or governance-sensitive work.
- `antigravity` owns low-risk, narrow, low-surface-area tasks.
- If a task starts small but becomes governance-sensitive or cross-cutting, escalate to `Codex`.

## 9. Stop and escalate conditions

Stop and escalate when any of the following is true:

- the request crosses a forbidden path or protected runtime boundary
- the task cannot be mapped to a Stage or Checklist item
- the evidence chain cannot be made concrete
- the requested change would weaken determinism, SSOT-only behavior, or the single-writer boundary
- the change would introduce repo-tracked secrets or runtime artifacts

## 10. PR body alignment

The root PR template must stay aligned with this file and include at least:

- `Stage`
- `Checklist item`
- `Plane`
- `DoD improved`
- `Summary of change`
- `Files changed`
- `Evidence`
- `Tests run`
- `Expected SSOT/output impact`
- `Degrade`
- `Kill switch / rollback`
- `Legacy Impact`
- `Out of scope / not changed`
