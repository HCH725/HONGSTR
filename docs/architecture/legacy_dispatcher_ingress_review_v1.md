# HONGSTR Legacy Dispatcher Ingress Review v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-only / audit-first / removal-plan-first / no runtime wiring
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: legacy dispatcher ingress review / removal candidate hardening
Plane: Governance docs across State Plane / Control Plane / Research Plane
Expected SSOT/output impact: none

## 0. Purpose

This review inventories legacy dispatcher ingress paths and adjacent non-Telegram execution entrypoints, then classifies them as:

- `Keep`
- `Deprecated but keep for now`
- `Archive-only`
- `Removal candidate`
- `Safe remove now`

This document is intentionally audit-first. It does not retire workflows, scripts, or templates in this PR.

Follow-up status:

- the direct `/dispatch` chain reviewed here was retired by `docs/architecture/direct_dispatch_retirement_v1.md`
- the direct `/dispatch` rows below remain the pre-retirement audit basis for that decision
- bounded `/selfheal` disposition is now defined by `docs/architecture/bounded_selfheal_disposition_v1.md`
- self-heal remained intentionally out of scope for the direct `/dispatch` retirement PR

## 1. Decision Rules

An item is `Removal candidate` when all of the following hold:

- it forms, or materially enables, operator-triggered agent execution outside Telegram
- it conflicts with the Stage 7 single-entry target
- it is still referenced or wired strongly enough that removing it now should happen only in a dedicated follow-up PR

An item is `Archive-only` when:

- it is a historical doc or artifact
- it no longer defines canonical policy
- it should remain frozen until the underlying legacy chain is retired

An item is `Deprecated but keep for now` when:

- it is an alternate ingress or support surface outside Telegram
- it is still guarded or bounded enough that removing it immediately would be premature
- it needs a separate design decision or replacement path first

`Safe remove now` requires:

- no runtime role
- no active workflow or script dependency
- no meaningful remaining references
- no impact on Stage 2, Stage 7, or Stage 8 invariants

## 2. Ingress Inventory

### 2.1 Direct legacy `/dispatch` chain

| Path | Ingress type | Trigger | Still referenced | Telegram single-entry conflict | Stage risk | Classification | Reason | Evidence | Next action | Removal plan |
|---|---|---|---|---|---|---|---|---|---|---|
| `.github/workflows/dispatch.yml` | direct operator-triggered workflow ingress | GitHub `issue_comment` containing `/dispatch` | yes | yes | Stage 7 high; Stage 2 medium; Stage 8 medium | `Removal candidate` | active alternate operator ingress outside Telegram; directly executes dispatcher script | workflow trigger at `.github/workflows/dispatch.yml`; invokes `bash scripts/dispatch/dispatch_issue.sh`; referenced in `docs/dispatcher_agent.md` and `docs/governance/ccpm_adoption.md` | freeze and retire in a dedicated PR | remove in same PR as `scripts/dispatch/dispatch_issue.sh` and task template cleanup |
| `scripts/dispatch/dispatch_issue.sh` | direct dispatcher executor | called by dispatch workflow | yes | yes | Stage 7 high; Stage 2 medium; Stage 8 medium | `Removal candidate` | performs issue-comment-driven patch / PR flow outside Telegram | called from `.github/workflows/dispatch.yml`; parses `/dispatch`; writes comments and opens PRs; references `docs/dispatcher_smoke.md` | keep frozen; do not expand | retire together with workflow and any dependent template/docs |
| `.github/ISSUE_TEMPLATE/task.yml` | dispatch-enabling template | GitHub issue form for dispatchable tasks | yes | yes | Stage 7 medium; Stage 8 low | `Removal candidate` | explicitly frames tasks as units dispatched via `/dispatch`; coupled to legacy chain | says "dispatched to an AI agent via `/dispatch`"; referenced by `docs/governance/ccpm_adoption.md` and implied by dispatcher docs | replace or remove when dispatch chain is retired | remove or rewrite into a non-dispatch generic task template in the same retirement slice |

### 2.2 Historical dispatcher docs and artifacts

| Path | Ingress type | Trigger | Still referenced | Telegram single-entry conflict | Stage risk | Classification | Reason | Evidence | Next action | Removal plan |
|---|---|---|---|---|---|---|---|---|---|---|
| `docs/dispatcher_agent.md` | historical dispatcher doc | none by itself | yes | yes, by describing alternate ingress | Stage 7 medium | `Archive-only` | already downgraded; should remain frozen until dispatch chain is retired | doc lists `.github/workflows/dispatch.yml`, `scripts/dispatch/dispatch_issue.sh`, `.github/ISSUE_TEMPLATE/task.yml` as historical assets | keep archived and non-canonical | delete or move to archive only after dispatch runtime chain is removed |
| `docs/dispatcher_smoke.md` | historical smoke artifact | none by itself | yes | indirect | Stage 7 low | `Archive-only` | not canonical, but still referenced by dispatcher script as `SMOKE_PATH` | `scripts/dispatch/dispatch_issue.sh` sets `SMOKE_PATH=\"docs/dispatcher_smoke.md\"` | keep frozen until dispatcher script is removed | remove together with dispatcher script retirement |
| `docs/governance/ccpm_adoption.md` | historical governance note | none by itself | yes | indirect | Stage 7 low | `Deprecated but keep for now` | broader governance note still exists, but `/dispatch` content is now historical only | explicitly calls `.github/workflows/dispatch.yml` and `.github/ISSUE_TEMPLATE/task.yml` historical | keep as historical note | trim or split dispatch-specific sections after dispatch chain retirement |

### 2.3 Bounded non-Telegram ingress still under review

| Path | Ingress type | Trigger | Still referenced | Telegram single-entry conflict | Stage risk | Classification | Reason | Evidence | Next action | Removal plan |
|---|---|---|---|---|---|---|---|---|---|---|
| `.github/workflows/self_heal.yml` | bounded repair ingress | GitHub `issue_comment` with `/selfheal` or `workflow_dispatch` | yes | yes, but bounded | Stage 7 medium; Stage 8 medium; Stage 2 low | `Deprecated but keep for now` | still non-Telegram ingress, but materially more guarded than `/dispatch` and already tied to allowlists/checks/draft PR only | workflow trigger lines show `issue_comment` and `workflow_dispatch`; uses `scripts/self_heal/run_required_checks.sh`; opens draft PR with review | keep under review; do not expand | decide in a separate PR whether to retire, sandbox further, or fold into a future bounded steward-approved path |
| `docs/self_heal.md` | bounded repair governance doc | none by itself | yes | indirect | Stage 7 medium | `Deprecated but keep for now` | documents a still-live non-Telegram ingress, but bounded and referenced by governance docs | doc trigger says `Issue comment contains: /selfheal`; referenced by `docs/architecture/agent_organization_governance_v1.md` and `docs/architecture/governance_dedupe_record_v1.md` | mark as bounded non-Telegram ingress under review | revisit when deciding the fate of `.github/workflows/self_heal.yml` |
| `.github/PULL_REQUEST_TEMPLATE/self_heal.md` | support asset, not ingress by itself | used by self-heal workflow PR creation | yes | no direct conflict by itself | Stage 8 low | `Keep` | support template only; removing it now adds no governance value while self-heal remains | `.github/workflows/self_heal.yml` uses `--body-file .github/PULL_REQUEST_TEMPLATE/self_heal.md` | keep as support asset | retire only if self-heal workflow is retired |

### 2.4 Guarded support paths, not ingress by themselves

| Path | Ingress type | Trigger | Still referenced | Telegram single-entry conflict | Stage risk | Classification | Reason | Evidence | Next action | Removal plan |
|---|---|---|---|---|---|---|---|---|---|---|
| `scripts/self_heal/enforce_allowed_paths.py` | support guard | invoked by self-heal workflow | yes | no direct conflict | Stage 8 low | `Keep` | guardrail support, not operator ingress | called twice by `.github/workflows/self_heal.yml` | keep | revisit only if self-heal architecture changes |
| `scripts/self_heal/run_required_checks.sh` | support guard | invoked by self-heal workflow | yes | no direct conflict | Stage 2 low; Stage 8 low | `Keep` | preflight guard support, not operator ingress | called by `.github/workflows/self_heal.yml` and referenced in `docs/self_heal.md` | keep | revisit only if self-heal architecture changes |
| `scripts/self_heal/parse_ticket.py` | support parser | invoked by self-heal workflow | yes | no direct conflict | Stage 8 low | `Keep` | parser support, not ingress | called by `.github/workflows/self_heal.yml` | keep | revisit only if self-heal architecture changes |
| `tests/test_self_heal_allowed_paths.py` | safety test | invoked by required checks | yes | no direct conflict | Stage 8 low | `Keep` | test coverage for bounded repair allowlist | referenced by `scripts/self_heal/run_required_checks.sh` and canonical governance docs | keep | revisit only if self-heal architecture changes |

## 3. Reference Summary

Pre-retirement repo-local findings from this review:

- the only `issue_comment` workflows in this ingress family were:
  - `.github/workflows/dispatch.yml`
  - `.github/workflows/self_heal.yml`
- the only `workflow_dispatch` workflow in this ingress family was:
  - `.github/workflows/self_heal.yml`
- the direct `/dispatch` chain was cross-linked through:
  - `.github/workflows/dispatch.yml`
  - `scripts/dispatch/dispatch_issue.sh`
  - `.github/ISSUE_TEMPLATE/task.yml`
  - `docs/dispatcher_agent.md`
  - `docs/governance/ccpm_adoption.md`
- `docs/dispatcher_smoke.md` was not free-floating noise because it was referenced by `scripts/dispatch/dispatch_issue.sh`

Post-retirement follow-up status:

- `.github/workflows/dispatch.yml` has been removed
- `scripts/dispatch/dispatch_issue.sh` has been removed
- `.github/ISSUE_TEMPLATE/task.yml` has been removed
- `docs/dispatcher_agent.md` has been removed
- `docs/dispatcher_smoke.md` has been removed
- `.github/workflows/self_heal.yml` remains the only non-Telegram ingress in this review family and stays out of scope here

## 4. Conflict With Single Telegram Entrance

### Direct conflict

These items materially conflict with the Stage 7 target because they let GitHub issue comments initiate agent work outside Telegram:

- `.github/workflows/dispatch.yml`
- `scripts/dispatch/dispatch_issue.sh`
- `.github/ISSUE_TEMPLATE/task.yml`

### Bounded but still divergent

These items also bypass Telegram, but with materially stronger containment:

- `.github/workflows/self_heal.yml`
- `docs/self_heal.md`

They should not be treated as equivalent to `/dispatch`, but they still need a later architecture decision because they remain non-Telegram operator ingress.

## 5. Safe Remove Now

At the time of the audit snapshot, no item qualified as `Safe remove now`.

Reason:

- every dispatcher-path doc or artifact was still referenced by an active workflow, script, or historical governance note
- every self-heal path was still either active or required by the bounded repair chain
- removing any one of these in isolation would have left partial legacy wiring, broken references, or an undocumented behavior gap

Post-retirement update:

- the dedicated direct `/dispatch` retirement PR has now removed the dispatcher chain as one smallest unit
- the remaining self-heal paths still do not qualify as `Safe remove now`

## 6. Stage Risk Summary

### Stage 2

- risk is indirect but real if alternate ingress paths evolve into competing writers or non-deterministic control-plane truth
- no current evidence shows a second state writer here, but keeping multiple operator ingresses increases governance drift risk

### Stage 7

- this is the primary risk area
- `/dispatch` directly conflicts with the Telegram single outward operator entrance
- `/selfheal` is now classified separately as sandbox-only rather than a production bounded exception

### Stage 8

- bounded repair, allowlist, and cooldown/dedupe remain valid only if these alternate ingresses stay narrow and review-driven
- `/dispatch` is weakly aligned with Stage 8 compared with self-heal because it is a broader task-execution path

## 7. Recommended Smallest-Unit Follow-On Sequence

1. completed: retirement PR for the direct `/dispatch` chain only:
   - `.github/workflows/dispatch.yml`
   - `scripts/dispatch/dispatch_issue.sh`
   - `.github/ISSUE_TEMPLATE/task.yml`
   - `docs/dispatcher_agent.md`
   - `docs/dispatcher_smoke.md`
   - dispatch-specific historical sections in `docs/governance/ccpm_adoption.md`
2. completed: separate review PR for bounded non-Telegram self-heal ingress:
   - current disposition is sandbox-only; later runtime PR decides containment vs retirement
3. only after those decisions, clean up any remaining labels/templates/docs that mention dispatch or self-heal

## 8. Degrade / Kill Switch / Removal Plan

Degrade:

- keep this review docs-only
- freeze legacy ingress surfaces rather than partially removing them

Kill switch:

- close this stacked PR or revert the docs commit
- runtime behavior remains unchanged

Removal plan:

- keep the direct `/dispatch` chain retired via its dedicated smallest-unit PR
- do not mix self-heal retirement with dispatch retirement unless the policy decision is explicit
- preserve evidence of the legacy paths in governance docs or release notes after retirement
