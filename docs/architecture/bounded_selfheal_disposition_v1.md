# HONGSTR Bounded Self-Heal Disposition v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / policy-first / disposition-first / no runtime wiring
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: bounded `/selfheal` disposition PR
Plane: Governance docs across Control Plane / State Plane / bounded repair support paths
Expected SSOT/output impact: none

Containment update:

- the GitHub `issue_comment` ingress has been removed from `.github/workflows/self_heal.yml`
- `workflow_dispatch` remains as the only live manual sandbox-only path
- support scripts, tests, and tg_cp / SSOT boundaries remain unchanged

## 0. Scope

This review covers the bounded `/selfheal` chain only:

- `.github/workflows/self_heal.yml`
- `docs/self_heal.md`
- `.github/PULL_REQUEST_TEMPLATE/self_heal.md`
- `scripts/self_heal/enforce_allowed_paths.py`
- `scripts/self_heal/run_required_checks.sh`
- `scripts/self_heal/parse_ticket.py`
- `scripts/self_heal/build_patch_from_anchor.py`
- `tests/test_self_heal_allowed_paths.py`

This PR does not process:

- `_local/telegram_cp/**`
- `src/hongstr/**`
- any state writer or `data/state/*` consumer path
- direct `/dispatch` assets already retired by `docs/architecture/direct_dispatch_retirement_v1.md`
- any Obsidian / LanceDB runtime or control-plane wiring

## 1. Direct Answer

`/selfheal` does not qualify as a production `bounded exception`.

Recommended disposition:

- treat `/selfheal` as `sandbox-only`
- keep the support guard/test assets
- keep the live workflow/doc surface frozen and non-expanding
- keep the remaining manual `workflow_dispatch` path as a deprecated sandbox-only route until a later retirement decision

Why this is the recommended disposition:

- it still creates a non-Telegram operator ingress through manual GitHub `workflow_dispatch`
- it mutates repo state by creating branches, commits, pushes, and draft PRs
- it is materially more bounded than the retired direct `/dispatch` chain because it re-runs `allowed_paths`, runs required checks, requests review, and never auto-merges
- the current patch builder is narrow and deterministic rather than a free-form agent executor

Short answer by label:

- `bounded exception`: no, not for production governance
- `sandbox-only`: yes, this is the current recommended posture
- `retirement candidate`: yes, for the remaining manual `workflow_dispatch` path if sandbox-only containment should not remain long-term

## 2. Current Chain And Evidence

### 2.1 What the workflow does today

Concrete repo-local findings:

- `.github/workflows/self_heal.yml` accepts only `workflow_dispatch`
- the workflow validates a JSON repair ticket via `scripts/self_heal/parse_ticket.py`
- it creates a branch, stages a generated patch, runs `scripts/self_heal/enforce_allowed_paths.py`, runs `bash scripts/self_heal/run_required_checks.sh`, commits, pushes, and opens a draft PR
- the workflow no longer comments back to GitHub issues because the issue-comment ingress was removed

### 2.2 Why it is still bounded

Bounded characteristics that are present now:

- `allowed_paths` gate runs before and after the final restage
- required checks run before commit/push
- PR creation is draft-only
- review is requested
- no auto-merge path is defined
- `scripts/self_heal/build_patch_from_anchor.py` is currently hardcoded to `docs/tg_cp_watchdog.md` and one specific insert line, so the current implementation is narrow rather than arbitrary

### 2.3 Where governance drift exists

The chain is not fully aligned with current governance:

- Stage 7 conflict remains because manual `workflow_dispatch` is still a non-Telegram operator ingress
- `docs/self_heal.md` historically described broader sample scopes such as `_local/telegram_cp/`, while the current workflow implementation is much narrower
- no explicit cooldown/dedupe policy is defined for `/selfheal`
- pausability exists operationally by disabling the workflow, but that kill switch was not previously captured as the canonical disposition

## 3. Stage Alignment

### Stage 2

Current alignment:

- no evidence of a second canonical `data/state/*` writer
- `scripts/guardrail_check.sh` is part of required checks
- the chain does not publish `/status` or `/daily` truth

Residual risk:

- any future widening of allowed paths or target files could drift toward non-canonical mutation paths if governance weakens

### Stage 7

Current conflict:

- `/selfheal` is still a non-Telegram ingress
- only manual `workflow_dispatch` remains as the ingress outside the central steward

Disposition implication:

- this prevents `/selfheal` from being treated as a production single-entry-compliant path
- sandbox-only is the strictest posture that matches the current implementation without doing runtime wiring in this PR

### Stage 8

Current partial alignment:

- allowlist is present
- bounded repair checks are present
- PR-based review is present
- the flow is pausable by disabling the workflow

Current gaps:

- `/selfheal` is not report-only
- no explicit cooldown/dedupe contract is attached to the workflow
- therefore it fits a bounded repair sandbox better than a generally approved production ingress

## 4. Inventory And Classification

### 4.1 Ingress surfaces

| Surface | Current role | Classification | Reason | Evidence | Next action | Removal plan |
|---|---|---|---|---|---|---|
| `.github/workflows/self_heal.yml` `issue_comment` trigger | retired ingress | `Removed now` | direct GitHub comment ingress conflicted most clearly with the Stage 7 single-entry target and has now been contained out of the workflow | runtime-only containment removed `on: issue_comment`, the comment-body gate, and issue comment-back steps | keep removed | do not reintroduce without a separate approved PR |
| `.github/workflows/self_heal.yml` `workflow_dispatch` trigger | manual bounded repair ingress | `Deprecated but keep for now` | still outside Telegram, but now the only remaining ingress and therefore easier to contain as sandbox-only | workflow `on: workflow_dispatch`; accepts `ticket_json` and optional `dry_run` | keep manual-only posture in docs; no expansion | later runtime PR should decide whether to keep as sandbox-only or retire the remaining manual path |

### 4.2 Path inventory

| Path | Current role | Classification | Reason | Evidence | Next action | Removal plan |
|---|---|---|---|---|---|---|
| `.github/workflows/self_heal.yml` | active bounded repair workflow | `Deprecated but keep for now` | workflow still exists and is materially bounded, but it is not Stage 7 single-entry compliant as a production ingress | branch/commit/push/draft PR steps; dual ingress triggers; allowlist/check gates | keep frozen under sandbox-only posture | later runtime PR either manualizes further or retires it |
| `docs/self_heal.md` | compatibility note for current workflow shape | `Deprecated but keep for now` | useful as an implementation note, but it must not define canonical ingress policy | historical `/selfheal` trigger language; broader sample scope than the current hardcoded patch builder | keep with non-canonical status note | archive or remove if runtime chain is retired |
| `.github/PULL_REQUEST_TEMPLATE/self_heal.md` | support template for draft PRs | `Keep` | support asset only; no ingress by itself | workflow uses `--body-file .github/PULL_REQUEST_TEMPLATE/self_heal.md` | keep | retire only if workflow is retired |
| `scripts/self_heal/enforce_allowed_paths.py` | allowlist guard | `Keep` | central bounded-repair guardrail; not an ingress by itself | workflow runs it twice; tests cover matcher behavior | keep | revisit only if self-heal architecture changes |
| `scripts/self_heal/run_required_checks.sh` | bounded-repair preflight | `Keep` | keeps guardrail check and self-heal safety test coupled to the workflow | workflow calls it before commit/push | keep | revisit only if self-heal architecture changes |
| `scripts/self_heal/parse_ticket.py` | repair-ticket validator | `Keep` | schema gate for required keys; not an ingress by itself | workflow validates `tmp/ticket.json` through it | keep | revisit only if self-heal ticket contract changes |
| `scripts/self_heal/build_patch_from_anchor.py` | deterministic patch builder | `Keep` | current implementation is narrow and path-specific, which helps prevent arbitrary execution | hardcoded `TARGET_PATH = "docs/tg_cp_watchdog.md"` and fixed insert line | keep frozen; do not generalize in-place | if self-heal is retired, remove together with the workflow |
| `tests/test_self_heal_allowed_paths.py` | safety test for allowlist gate | `Keep` | verifies allowlist matcher and changed-path collection fallback behavior | run by `scripts/self_heal/run_required_checks.sh` | keep | revisit only if guard behavior changes |

### 4.3 Safe remove now

No bounded `/selfheal` path qualifies as `Safe remove now`.

Reason:

- the workflow is still live
- the support scripts and template are still active dependencies of that workflow
- removing any one of them in isolation would either break the bounded repair chain or leave documentation drift without actually resolving the Stage 7 ingress conflict

### 4.4 Archive-only

No bounded `/selfheal` path is `Archive-only` yet.

Reason:

- unlike the retired direct `/dispatch` docs, these assets still describe or support a live workflow

## 5. Policy Guardrails For The Current Posture

While the workflow remains in the repo, the governance posture should be:

- sandbox-only
- no expansion of allowed paths beyond explicitly reviewed governance/support paths
- no arbitrary target-file selection
- no auto-merge
- no conversion into a Telegram-adjacent or publicly advertised operator entrance
- no widening into `src/hongstr/**`, state-writer paths, or control-plane runtime mutation

This means:

- `/selfheal` may remain as a bounded repair sandbox while policy and runtime are reviewed
- it must not be presented as part of the target production single-entry model
- any future runtime change should be a separate smallest-unit PR

## 6. Degrade / Kill Switch / Removal Plan

Degrade:

- keep this PR docs-only
- keep current runtime behavior unchanged
- treat `/selfheal` as frozen and non-expanding until a separate runtime PR lands

Kill switch:

- close this stacked PR, or
- revert the docs commit with `git revert <commit_sha>`

Operational kill switch for the live workflow, if needed later:

- disable the `L2 Self-Heal` GitHub workflow, or
- retire the remaining manual `workflow_dispatch` path in a dedicated runtime PR

Removal plan:

1. keep support guards/tests/template while the workflow remains live
2. decide in a later runtime PR whether to:
   - keep manual `workflow_dispatch` as a sandbox-only escape hatch, or
   - retire the entire workflow/template/support chain
3. if the workflow is retired, then archive or remove `docs/self_heal.md` and remove now-orphaned support assets in the same smallest-unit PR
