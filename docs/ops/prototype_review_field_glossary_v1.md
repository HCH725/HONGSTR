# HONGSTR Prototype Review Field Glossary v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / glossary-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype review field glossary PR
Plane: central steward prototype review/package governance
Expected SSOT/output impact: none
Runtime impact: none (docs-only)
Rollout relation: governance-only; not rollout approval
Kill switch: HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0
Canonical truth boundary: does not change canonical SSOT or `/status` `/daily` `/dashboard`; does not write `data/state/*`

Boundary reminder:

- This document is not a rollout authorization.
- This document does not authorize formal Telegram alerting.
- This document is not canonical SSOT.
- This document does not change `/status` `/daily` `/dashboard` truth sources.
- This document does not permit writes to `data/state/*`.
- This document has no runtime wiring effect.
- This document does not authorize bounded repair.

## 0. Purpose

This glossary standardizes the recurring fields and terms used across the central steward shadow/prototype review package.

Use it to answer:

- what a field means
- when a field should appear
- whether the field is required or optional
- which templates use it
- what common field drift or misuse to avoid

This glossary is governance-only.

It does not:

- authorize rollout
- authorize formal Telegram alerting
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- change `tg_cp` runtime

Core rule:

- field alignment improves governance consistency only
- `glossary != rollout approval`

## 1. Scope

This glossary applies only to the prototype review/package chain around the current central steward shadow/prototype path.

It covers fields and terms used in:

- evidence summary
- upgrade-review
- retirement-review
- reviewer request-changes note
- decision record
- author and reviewer checklists
- resubmission checklist
- example packages

It does not define:

- canonical `data/state/*` schema
- `src/hongstr/**` runtime contracts
- Telegram message payloads
- rollout-specific runtime flags beyond boundary reminders already documented elsewhere

## 2. Field Rules

Read these rules before using any term below.

- Use the same field meaning across templates unless a template explicitly narrows it.
- Do not reinterpret a governance field as canonical system state.
- Do not reuse glossary fields as `/status`, `/daily`, or `/dashboard` truth.
- If a value is unknown, say `unknown` and explain why instead of inventing precision.
- If a field is not applicable, mark it clearly as `not applicable` rather than deleting it silently.

## 3. Glossary

### 3.1 `review_id`

- Definition: the unique identifier for one review or re-review record.
- When used: every live review template, request-changes note, decision record, and resubmission flow artifact.
- Templates using it:
  - `docs/templates/prototype_upgrade_review_template_v1.md`
  - `docs/templates/prototype_retirement_review_template_v1.md`
  - `docs/templates/prototype_review_decision_record_template_v1.md`
  - `docs/templates/prototype_review_request_changes_note_template_v1.md`
  - `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- Required or optional: required.
- Common misuse:
  - using a vague label like `prototype-review`
  - changing the ID mid-review without reason
  - omitting the review type or date component
- Example value: `prototype-upgrade-review-20260306`

### 3.2 `prototype_id`

- Definition: the stable slug for the prototype under review.
- When used: whenever the document must distinguish which prototype the package refers to.
- Templates using it:
  - `docs/templates/prototype_evidence_summary_template_v1.md`
  - `docs/templates/prototype_review_decision_record_template_v1.md`
- Required or optional: required where present; default value in v1 is fixed.
- Common misuse:
  - inventing a new slug for the same path
  - replacing the slug with human prose only
- Example value: `central-steward-shadow-prototype`

### 3.3 `review_type`

- Definition: the type of governance review being performed.
- When used: every review package and any related request-changes or decision record.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - decision record
  - request-changes note
  - author/reviewer/resubmission checklists
- Required or optional: required.
- Allowed values:
  - `upgrade-review`
  - `retirement-review`
  - `evidence-review` only where the template explicitly allows it
- Deprecated aliases:
  - `upgrade`
  - `retirement`
- Common misuse:
  - mixing `upgrade-review` and `retirement-review` in the same package
  - using a rollout label instead of a review label
  - switching label style inside one package without explanation
- Example value: `upgrade-review`

### 3.4 `review_window`

- Definition: the observation period the evidence is based on.
- When used: all substantive review artifacts and evidence summaries.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - decision record
- Required or optional: required for live reviews; optional only in reusable examples.
- Common misuse:
  - omitting dates after citing evidence
  - using vague terms like `recently`
  - using a different window in evidence summary and review template without explanation
- Example value: `2026-03-01..2026-03-14`

### 3.5 `reviewer`

- Definition: the human reviewer or governance reviewer responsible for examining the package.
- When used: all review-facing templates, request-changes notes, and decision records.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - reviewer checklist
  - decision record
  - request-changes note
- Required or optional: required.
- Common misuse:
  - leaving it blank in a final decision artifact
  - confusing reviewer with review author
- Example value: `hong`

### 3.6 `author`

- Definition: the person who assembled or resubmitted the review package.
- When used: author checklist, review templates, decision record, resubmission checklist, request-changes note.
- Templates using it:
  - evidence summary as `author`
  - upgrade-review template as `author`
  - retirement-review template as `author`
  - decision record as `author`
  - request-changes note as `author`
  - resubmission checklist as `author`
- Required or optional: required.
- Common misuse:
  - using reviewer and author interchangeably
  - omitting the author in a resubmission artifact
  - using deprecated alias `review_author` in new review packages
- Example value: `hong`

### 3.7 `evidence summary`

- Definition: the structured summary of observed evidence collected under the approved observation plan.
- When used: before or alongside any review template; often reused during resubmission.
- Templates using it:
  - `docs/templates/prototype_evidence_summary_template_v1.md`
  - referenced by all review templates, checklists, request-changes notes, and decision records
- Required or optional: required for `upgrade-review` and normal `retirement-review`; may be incomplete only when explicitly marked insufficient.
- Common misuse:
  - treating it as a final decision
  - writing free-form prose instead of structured fields
  - back-filling canonical state from it
- Example value: `prototype-central-steward-shadow-prototype-upgrade-review-20260301_20260314-evidence-summary.md`

### 3.8 `decision_value`

- Definition: how much net-new understanding the prototype added beyond canonical SSOT and formal alerting.
- When used: evidence summary and both review templates.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
- Required or optional: required.
- Common misuse:
  - equating “interesting” with decision value
  - claiming value without saying what changed for the reviewer/operator
- Example value: `low-value; repeated existing watchdog context without new diagnosis`

### 3.9 `canonical_overlap`

- Definition: how much the prototype output simply restates canonical SSOT or already-visible formal alerts.
- When used: evidence summary, `upgrade-review`, `retirement-review`, request-changes discussions.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
- Required or optional: required.
- Common misuse:
  - treating low overlap as automatic upgrade approval
  - not distinguishing overlap with SSOT versus overlap with formal alerts
- Example value: `medium; 3 of 7 summaries repeated existing watchdog state`

### 3.10 `false_positive_noise`

- Definition: summaries that did not improve understanding or that were ambiguous, repetitive, or operationally unhelpful. In prose this may still be described as false positive / noise, but the field label should stay `false_positive_noise`.
- When used: evidence summary and review templates, especially when deciding whether to keep or retire.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - resubmission checklist as a required re-check
- Required or optional: required where evidence is being evaluated.
- Common misuse:
  - counting all activity as noise
  - ignoring ambiguity risk because the path is still internal-only
  - replacing the canonical field label with ad hoc prose in structured tables
- Example value: `2 noisy summaries out of 6 because wording duplicated existing state without new context`

### 3.11 `recovery_of`

- Definition: the relationship between a recovery event and the earlier alert/event it closes; in review docs this usually appears as `recovery_of_ratio`.
- When used: evidence summary and review templates when assessing closure versus churn.
- Templates using it:
  - evidence summary as `recovery_of_ratio`
  - upgrade-review template as `recovery_of_ratio`
  - retirement-review template as `recovery_of_ratio`
- Required or optional: required in evidence fields where the ratio is listed; the direct raw field may be absent from docs if only the ratio is being reviewed.
- Common misuse:
  - treating every recovery as inherently useful
  - confusing the upstream alert relation with a final governance decision
- Example value: `recovery_of_ratio = 0.25`

### 3.12 `request_changes_reason`

- Definition: the normalized category explaining why a reviewer returned the package for fixes.
- When used: request-changes note and any resubmission work that closes the note.
- Templates using it:
  - `docs/templates/prototype_review_request_changes_note_template_v1.md`
  - referenced by `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- Required or optional: required when a request-changes note is issued.
- Allowed values:
  - `insufficient evidence`
  - `incomplete template`
  - `boundary unclear`
  - `rollout mixed into review PR`
  - `canonical overlap unclear`
  - `observation window incomplete`
  - `other`
- Common misuse:
  - using broad prose only with no fixed category
  - mixing several different blockers without naming them clearly
- Example value: `boundary unclear`

### 3.13 `assessment status`

- Definition: the provisional evidence-summary posture recorded before a final review decision exists.
- When used: evidence summary and package assembly examples when the docs are still expressing review readiness rather than a final outcome.
- Templates using it:
  - evidence summary
  - package example notes
- Required or optional: required where a template includes an explicit assessment-status field.
- Governing record:
  - `docs/ops/prototype_assessment_status_alignment_record_v1.md`
- Allowed values:
  - `continue observation`
  - `candidate for upgrade-review`
  - `candidate for retirement-review`
  - `needs more evidence`
- Common misuse:
  - using `keep` as a preliminary assessment label instead of the canonical observation posture
  - using `insufficient evidence` as a preliminary assessment label instead of `needs more evidence`
  - treating `candidate for upgrade-review` or `candidate for retirement-review` as final decision outcomes
  - leaving the field unlabeled so assessment status, decision outcome, and next action blur together
- Example value: `continue observation`

### 3.14 `reviewer response state`

- Definition: the normalized reviewer-side workflow state used when the package is being returned, gated for re-review, or handed off to the final decision record.
- When used: reviewer checklist, request-changes note, resubmission flow, and resubmission example.
- Templates using it:
  - reviewer checklist
  - request-changes note
  - re-review resubmission checklist
  - resubmission example
- Required or optional: required where a template includes an explicit reviewer response-state field or response-state guardrail note.
- Governing record:
  - `docs/ops/prototype_reviewer_response_state_alignment_record_v1.md`
- Allowed values:
  - `request-changes note required`
  - `return for fixes`
  - `re-review allowed after fixes`
  - `ready for decision record`
- Common misuse:
  - using `request changes` or `request-changes note` as if they were the response-state label itself
  - using `insufficient evidence for decision` as a reviewer response-state enum instead of request-changes reason or decision outcome wording
  - putting reviewer response states inside the final decision outcome enum
  - leaving the state implied by prose only when a structured label is available
- Example value: `ready for decision record`

### 3.15 `decision outcome`

- Definition: the fixed governance result recorded after review or re-review.
- When used: reviewer checklist, decision record, and review templates.
- Templates using it:
  - reviewer checklist
  - decision record
  - upgrade-review
  - retirement-review
- Required or optional: required in final decision artifacts.
- Allowed values:
  - `keep`
  - `upgrade-review pass`
  - `upgrade-review fail`
  - `retirement-review pass`
  - `retirement-review fail`
  - `insufficient evidence`
- Common misuse:
  - inventing a new status like `soft pass`
  - treating `request changes` as a final decision outcome instead of a return-for-fixes state
  - treating reviewer response states such as `request-changes note required`, `return for fixes`, `re-review allowed after fixes`, or `ready for decision record` as final decision outcomes
  - treating `continue observation` or `needs more evidence` as final decision outcomes instead of assessment status or next action
  - treating assessment-only labels like `candidate for upgrade-review` or `candidate for retirement-review` as final decision outcomes
  - combining `insufficient evidence` with `continue observation` into one pseudo-enum
- Example value: `keep`

### 3.16 `next action`

- Definition: the smallest allowed follow-on step after the current review state or decision.
- When used: evidence summary, review templates, decision record, reviewer notes.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - decision record
  - reviewer checklist
- Required or optional: required where the template includes an explicit action block.
- Governing record:
  - `docs/ops/prototype_decision_next_action_alignment_record_v1.md`
- Allowed values:
  - `continue observation`
  - `extend evidence window`
  - `open review PR`
  - `open retirement PR`
  - `no action`
- Common misuse:
  - using rollout language inside a review-only artifact without separate approval
  - using stage-specific prose like `open upgrade review`, `open retirement review`, or `open rollout candidate PR` instead of the canonical labels
  - skipping the action even when the decision is recorded
- Example value: `continue observation`

### 3.17 `boundary check labels`

- Definition: the canonical wording used for structured boundary-check rows, field labels, and checklist labels across the prototype review/package docs.
- When used: evidence summary, upgrade-review, retirement-review, decision record, author checklist, reviewer checklist, resubmission checklist, and examples.
- Governing record:
  - `docs/ops/prototype_boundary_check_row_alignment_record_v1.md`
- Canonical labels:
  - `internal-only`
  - `not-canonical`
  - does not affect `/status`
  - does not affect `/daily`
  - does not affect `/dashboard`
  - does not write `data/state/*`
  - does not create a second state writer
  - does not change `tg_cp` runtime
  - does not touch bounded repair
  - `review PR != rollout PR`
- Common misuse:
  - mixing `affects`, `does not change`, and `no impact` for the same boundary
  - adding `truth` to `/dashboard` in some files but not others
  - padding the same label with `still`, `remains`, or `at review time` inside structured rows
  - using `touches tg_cp runtime` instead of the normalized runtime-impact label
  - using `not a rollout PR` in one checklist and `disguised rollout PR` in another without the shared canonical label
- Example value: does not affect `/status`

## 4. Common Drift To Avoid

Do not let any of these drift patterns enter the package:

- using `reviewer`, `author`, and `review_author` inconsistently without context
- changing enum labels between templates
- using `decision_value` as a synonym for “I like this”
- using `canonical_overlap` without saying what it overlaps with
- using `request changes` prose without a fixed reason category
- turning glossary terms into rollout or canonical state language

## 5. Non-Rollout Reminder

Interpret this glossary correctly:

- it standardizes documentation terms only
- it does not approve runtime rollout
- it does not change canonical SSOT
- it does not change `/status`, `/daily`, or `/dashboard`

## 6. Canonical Answer

The canonical v1 answer is:

- use one shared meaning for recurring review fields
- keep enum values fixed
- mark required versus optional consistently
- call out common misuse early
- treat this glossary as governance alignment only, never as rollout approval
