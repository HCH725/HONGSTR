# HONGSTR Prototype Review Kickoff SOP v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / SOP-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype review kickoff SOP PR
Plane: central steward prototype review governance
Expected SSOT/output impact: none

## 0. Purpose And Scope

This SOP defines how a future review may be formally started for the current central steward shadow/prototype path.

It covers only:

- `upgrade review`
- `retirement review`

It does not authorize:

- rollout
- formal Telegram alerting
- bounded repair
- canonical state publication
- any change to `/status`, `/daily`, or `/dashboard` truth sources

Core rule:

- a review PR is not a rollout PR
- no rollout PR may start until the kickoff conditions in this SOP are satisfied and the review result is documented separately
- authors should complete `docs/templates/prototype_review_pr_author_checklist_v1.md` before opening any review PR

## 1. Definitions

### 1.1 Upgrade Review

`Upgrade review` means:

- a governance review that asks whether the prototype may move from `internal-log only` toward a later, separately reviewed, operator-visible but explicitly non-canonical shadow summary

`Upgrade review` does not mean:

- rollout
- formal alerting
- canonical state
- direct runtime activation

### 1.2 Retirement Review

`Retirement review` means:

- a governance review that asks whether the prototype should be archived or removed because its value is too low, its overlap/noise is too high, or its existence is creating boundary erosion pressure

`Retirement review` does not mean:

- immediate removal in the same kickoff step
- mixing archive/removal with unrelated runtime work

## 2. Who May Start A Review

Allowed initiators:

- the author of a dedicated review PR, if that PR includes all required evidence and the correct template
- a human governance reviewer for the central steward path, if they explicitly sponsor the review

Additional rule for `retirement review`:

- a human governance reviewer may start it directly when there is documented boundary erosion risk, confusion pressure, or prototype drift, even if the motivation is to stop the path rather than expand it

Not sufficient on its own:

- curiosity
- “this feels useful”
- “this seems noisy”
- a desire to skip directly to rollout

## 3. Required Inputs Before Kickoff

These items are mandatory before any formal review kickoff.

### 3.1 Shared prerequisites

Required for both `upgrade review` and `retirement review`:

- the current evidence plan is still the governing plan:
  - `docs/architecture/prototype_evidence_collection_plan_v1.md`
- the lifecycle criteria are still the governing criteria:
  - `docs/architecture/prototype_retirement_criteria_v1.md`
- the prototype still remains:
  - default-off
  - internal-only
  - not-canonical
  - non-actioning
- the kickoff PR is review-only and does not include rollout wiring

### 3.2 Upgrade review prerequisites

All of the following must be true:

- the evidence window has completed
- the minimum observation bar has been met:
  - `14 calendar days`
  - `at least 5 manual observation sessions`
- an evidence summary already exists
- `docs/templates/prototype_upgrade_review_template_v1.md` can be fully completed
- the review author can point to specific evidence for:
  - shadow summary generation frequency
  - dedupe hit rate
  - cooldown hit rate
  - `recovery_of` ratio
  - false positive / noise
  - decision value
  - canonical overlap

### 3.3 Retirement review prerequisites

Normally all of the following must be true:

- the evidence window has completed
- the minimum observation bar has been met:
  - `14 calendar days`
  - `at least 5 manual observation sessions`
- an evidence summary already exists
- `docs/templates/prototype_retirement_review_template_v1.md` can be fully completed

Exception:

- a human governance reviewer may start a retirement review before the full observation window completes if there is documented boundary erosion, canonical confusion risk, or repeated misuse pressure

If that exception is used, the kickoff PR must explicitly state:

- why the normal observation window was not enough or not appropriate
- what boundary risk is being contained
- why immediate retirement review is safer than waiting

## 4. Mandatory Materials At Kickoff

Every kickoff PR must include all of the following:

- the correct review template:
  - `docs/templates/prototype_upgrade_review_template_v1.md`
  - or `docs/templates/prototype_retirement_review_template_v1.md`
- an evidence summary derived from the approved evidence plan
- the observation window used for the review
- the current recommendation:
  - `keep`
  - `upgrade-review pass`
  - `retirement-review pass`
  - or `insufficient evidence / continue observation`
- links to related architecture docs:
  - `docs/architecture/prototype_evidence_collection_plan_v1.md`
  - `docs/architecture/prototype_retirement_criteria_v1.md`
  - `docs/architecture/shadow_summary_disposition_v1.md`
  - `docs/architecture/central_steward_readonly_ingest_v1.md`

If any required material is missing:

- the review must not start

## 5. When Review Must Not Start

Do not start `upgrade review` or `retirement review` when any of the following is true:

- the evidence window is incomplete and no retirement exception has been justified
- the minimum observation session count has not been met
- there is no written evidence summary
- the correct review template cannot be filled
- the prototype boundary is unclear or disputed
- the kickoff PR also tries to do rollout
- the kickoff PR also tries to change:
  - `src/hongstr/**`
  - `scripts/refresh_state.sh`
  - `scripts/state_snapshots.py`
  - `data/state/*`
  - `tg_cp` runtime behavior
- the proposal tries to make shadow output canonical
- the proposal mixes review with bounded repair, self-heal, or arbitrary execution
- the proposal mixes review with formal Telegram alerting

Upgrade-review specific stop conditions:

- message wording is not yet clearly non-canonical
- confusion risk with formal alerts is still unresolved
- the only argument for upgrade is operator preference without evidence

Retirement-review specific stop conditions:

- there is no concrete archive/remove scope
- there is no evidence of low value, high overlap, high noise, or boundary erosion
- the retirement PR is being used to smuggle unrelated cleanup

## 6. Kickoff Procedure

1. verify the review type:
   - `upgrade review`
   - or `retirement review`
2. verify the evidence window and session count
3. verify the correct template exists and can be filled completely
4. verify the review PR is review-only and not rollout
5. attach the evidence summary and related doc links
6. state the current recommendation clearly before requesting review

If any of the above fails:

- stop
- do not open the review PR yet
- continue observation or close the kickoff attempt

## 7. Allowed Review Outcomes

A completed review may conclude only with one of the following outcomes:

- `keep`
- `upgrade-review pass`
- `retirement-review pass`
- `insufficient evidence / continue observation`

Interpretation rule:

- `upgrade-review pass` still does not authorize rollout in the same PR
- `retirement-review pass` still does not authorize unrelated removal in the same PR
- `insufficient evidence / continue observation` means the current runtime posture stays unchanged

## 8. Review PR Is Not Rollout PR

Non-negotiable rule:

- a review PR must remain governance-only
- a rollout PR must be separate, later, and smaller

Therefore:

- no `upgrade review` PR may also enable operator-visible Telegram summary
- no `retirement review` PR may also remove unrelated runtime surfaces
- no review PR may alter canonical `data/state/*`
- no review PR may change `/status`, `/daily`, or `/dashboard` truth behavior

## 9. Stage Alignment

### 9.1 Stage 2

Kickoff SOP must preserve:

- single writer for `data/state/*`
- deterministic fallback
- SSOT-only top-level truth

Kickoff implication:

- if the proposed review blurs the state-writer boundary, do not start the review

### 9.2 Stage 7

Kickoff SOP must preserve:

- Telegram as the single operator entry surface
- read-only reporting
- minimal command surface

Kickoff implication:

- if the proposed review is actually trying to sneak in operator-visible behavior, do not start it as a review PR

### 9.3 Stage 8

Kickoff SOP must preserve:

- prototype
- report-only
- pausable
- allowlisted side path

Kickoff implication:

- if the review cannot stay within a pausable, non-P0, non-canonical posture, do not start it

## 10. Kill Switch / Rollback Note

Current kill switch remains:

- `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`

Kickoff rollback rule:

- if a review kickoff is found to be premature or out of scope, close the PR and return to observation mode
- do not compensate by widening runtime behavior

## 11. Recommended v1 Posture

Current recommendation in v1:

- do not start a review PR until the evidence plan window is actually satisfied
- require the correct template at kickoff time
- require a named human governance reviewer
- reject any attempt to merge review and rollout into one PR

Plain answer:

- review starts only after evidence is ready
- review uses the matching template
- review stays governance-only
- rollout, if ever approved later, must be a separate PR
