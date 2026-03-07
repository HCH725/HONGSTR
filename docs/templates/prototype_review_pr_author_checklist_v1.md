# HONGSTR Prototype Review PR Author Checklist v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / checklist-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype review PR author checklist PR
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

Use this checklist before opening any central steward shadow/prototype review PR.

This checklist is for authors only.

Reviewer-side validation belongs in `docs/templates/prototype_review_reviewer_checklist_v1.md`.
If this PR is being resubmitted after a `request-changes note`, also use `docs/templates/prototype_re_review_resubmission_checklist_v1.md`.
For canonical blocker-closure wording in that resubmission flow, use `docs/ops/prototype_required_fix_alignment_record_v1.md`.
For canonical blocker-closure status wording in that resubmission flow, use `docs/ops/prototype_blocker_closure_status_alignment_record_v1.md`.
For canonical blocker-evidence-reference wording in that resubmission flow, use `docs/ops/prototype_blocker_evidence_reference_alignment_record_v1.md`.
For canonical blocker-reference-target hint wording in that resubmission flow, use `docs/ops/prototype_blocker_reference_target_hint_alignment_record_v1.md`.
For canonical blocker-reference multiplicity hint wording in that resubmission flow, use `docs/ops/prototype_blocker_reference_multiplicity_hint_alignment_record_v1.md`.
For canonical blocker-reference ordering hint wording in that resubmission flow, use `docs/ops/prototype_blocker_reference_ordering_hint_alignment_record_v1.md`.
For canonical blocker-reference applicability hint wording in that resubmission flow, use `docs/ops/prototype_blocker_reference_applicability_hint_alignment_record_v1.md`.
For canonical blocker-reference placeholder shape wording in that resubmission flow, use `docs/ops/prototype_blocker_reference_placeholder_shape_alignment_record_v1.md`.
For canonical blocker-reference field-caption formatting in that resubmission flow, use `docs/ops/prototype_blocker_reference_field_caption_casing_alignment_record_v1.md`.
For canonical blocker-reference rendering rules in that resubmission flow, use `docs/ops/prototype_blocker_reference_rendering_exception_alignment_record_v1.md`.
For canonical blocker-reference live-field cue wording in that resubmission flow, use `docs/ops/prototype_blocker_reference_live_field_cue_alignment_record_v1.md`.
For canonical blocker-reference explanatory-inline cue wording in that resubmission flow, use `docs/ops/prototype_blocker_reference_explanatory_inline_cue_alignment_record_v1.md`.
For canonical blocker-reference live-vs-non-live contrast wording in that resubmission flow, use `docs/ops/prototype_blocker_reference_live_nonlive_contrast_alignment_record_v1.md`.

It does not replace:

- `docs/ops/prototype_review_kickoff_sop_v1.md`
- `docs/templates/prototype_evidence_summary_template_v1.md`
- `docs/templates/prototype_upgrade_review_template_v1.md`
- `docs/templates/prototype_retirement_review_template_v1.md`
- `docs/examples/prototype_review_package_example_v1.md`
- `docs/ops/prototype_review_package_naming_convention_v1.md`

It exists to prevent a review PR from being opened with missing evidence, missing boundary checks, or rollout drift.

## How To Use

1. choose the review type first:
   - `upgrade-review`
   - or `retirement-review`
2. complete this checklist before opening the PR
3. if any required item remains unchecked, do not open the review PR yet
4. copy the relevant review template into the review PR only after this checklist passes

## A. Shared Pre-Submit Checklist

- [ ] I have confirmed this is a `review PR`, not a rollout PR.
- [ ] I have confirmed this PR does not change `src/hongstr/**`.
- [ ] I have confirmed this PR does not change `scripts/refresh_state.sh`.
- [ ] I have confirmed this PR does not change `scripts/state_snapshots.py`.
- [ ] I have confirmed this PR does not change `data/state/*`.
- [ ] I have confirmed this PR does not change `_local/telegram_cp/**` runtime behavior.
- [ ] I have confirmed this PR does not enable formal Telegram alerting.
- [ ] I have confirmed this PR does not introduce bounded repair, self-heal, or arbitrary execution.
- [ ] I have re-read `docs/ops/prototype_review_kickoff_sop_v1.md`.
- [ ] I have re-read `docs/architecture/prototype_evidence_collection_plan_v1.md`.
- [ ] I have re-read `docs/architecture/prototype_retirement_criteria_v1.md`.

## B. Evidence Readiness Checklist

- [ ] The evidence window is complete.
- [ ] The minimum observation bar is met:
  - `14 calendar days`
  - `at least 5 manual observation sessions`
- [ ] An evidence summary already exists.
- [ ] The evidence summary uses `docs/templates/prototype_evidence_summary_template_v1.md`.
- [ ] The evidence summary includes:
  - shadow summary generation frequency
  - dedupe hit rate
  - cooldown hit rate
  - `recovery_of_ratio`
  - `false_positive_noise`
  - `decision_value`
  - `canonical_overlap`
- [ ] The evidence comes from approved non-canonical sources only.
- [ ] I have confirmed the evidence is not being turned into canonical state.
- [ ] I have confirmed the evidence is not being used to back-fill `/status`, `/daily`, or `/dashboard`.

## C. Review Type Checklist

- [ ] I have selected the correct review type:
  - `upgrade-review`
  - or `retirement-review`
- [ ] I have selected the correct review template for that review type.
- [ ] I can fill the selected template completely.

If this is an `upgrade-review`:

- [ ] I am using `docs/templates/prototype_upgrade_review_template_v1.md`.
- [ ] I have evidence that the proposal is still explicitly non-canonical.
- [ ] I have evidence that the proposal is still clearly distinct from a formal alert.

If this is a `retirement-review`:

- [ ] I am using `docs/templates/prototype_retirement_review_template_v1.md`.
- [ ] I have evidence for low value, high overlap, high noise, boundary erosion, or another retirement trigger.
- [ ] If I am using the early-retirement exception, a human governance reviewer is explicitly sponsoring it.

## D. Boundary Check Checklist

- [ ] I have re-confirmed the prototype is `internal-only` at the time of review.
- [ ] I have re-confirmed the prototype is `not-canonical`.
- [ ] I have re-confirmed the prototype does not affect `/status`.
- [ ] I have re-confirmed the prototype does not affect `/daily`.
- [ ] I have re-confirmed the prototype does not affect `/dashboard`.
- [ ] I have re-confirmed the prototype does not write `data/state/*`.
- [ ] I have re-confirmed the prototype does not create a second state writer.
- [ ] I have re-confirmed the prototype does not touch bounded repair.
- [ ] I have re-confirmed the prototype remains stoppable via `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`.

## E. Required Attachments Checklist

- [ ] The correct review template is attached or copied into the PR.
- [ ] The evidence summary is attached or linked.
- [ ] If this is a resubmission, the package includes the `review note reference` and, if applicable, the `closure evidence reference`, `fix evidence reference`, and `supporting evidence reference` fields.
- [ ] If this is a resubmission, those evidence references use canonical target hints such as `PR comment link`, `evidence summary section link`, `template diff link`, or `supporting doc link`.
- [ ] If this is a resubmission, those evidence references also use canonical multiplicity hints such as `single link`, `multiple links`, or `one-or-more links`.
- [ ] If this is a resubmission, those evidence references keep canonical ordering hints such as `review note first`, `closure evidence next`, `fix evidence next`, and `supporting evidence last` when multiple blocker-proof fields appear together.
- [ ] If this is a resubmission, those evidence references keep canonical applicability hints such as `if applicable`, `when requested`, `if present`, and `only when closure proof exists`.
- [ ] If this is a resubmission, those evidence references keep the canonical placeholder shape: `Applicability hint: ...`, `Ordering hint: ...`, then `<single link: ...>` / `<multiple links: ...>` / `<one-or-more links: ...>`.
- [ ] If this is a resubmission, those evidence references keep the canonical field captions: `Review note reference:`, `Closure evidence reference:`, `Fix evidence reference:`, and `Supporting evidence reference:`.
- [ ] If this is a resubmission, each `live blocker-evidence-reference field` stays stacked: every `live fill-in field` should appear as a `live field block`, not as non-live `explanatory prose`, a `compact table cell`, or an `inline placeholder-only fragment`.
- [ ] If this is a resubmission, non-live blocker-reference wording keeps the canonical cues: `explanatory prose`, `compact table cell`, and `inline placeholder-only fragment`.
- [ ] If this is a resubmission, the contrast sentences stay canonical: use `not a live fill-in field`, `outside the live field block`, and `in non-live context` when directly comparing live vs non-live blocker-reference wording.
- [ ] The observation window is stated clearly.
- [ ] The current recommendation is stated clearly:
  - `keep`
  - `upgrade-review pass`
  - `retirement-review pass`
  - or `insufficient evidence`
- [ ] The related docs are linked:
  - `docs/ops/prototype_review_kickoff_sop_v1.md`
  - `docs/architecture/prototype_evidence_collection_plan_v1.md`
  - `docs/architecture/prototype_retirement_criteria_v1.md`
  - `docs/architecture/shadow_summary_disposition_v1.md`
  - `docs/architecture/central_steward_readonly_ingest_v1.md`

## F. Non-Rollout Confirmation Checklist

- [ ] I have written explicitly that `review PR != rollout PR`.
- [ ] I have written explicitly that this PR does not enable operator-visible rollout.
- [ ] I have written explicitly that this PR does not alter canonical SSOT.
- [ ] I have written explicitly that any later rollout, if ever approved, must be a separate PR.

## G. Decision And Next Action Checklist

- [ ] I have written the current decision requested from reviewers.
- [ ] I have written the next action if the review passes.
- [ ] I have written the next action if the review fails.
- [ ] I have written the next action if evidence is insufficient.

## H. Kill Switch / Rollback Checklist

- [ ] I have stated the current kill switch: `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`.
- [ ] I have written the rollback note.
- [ ] I have confirmed rollback does not require changing canonical `data/state/*`.

## I. Author Final Gate

Do not open the review PR until every required checkbox above is checked.

Author sign-off:

- `review_type`: `<upgrade-review / retirement-review>`
- `author`: `<name or handle>`
- `date`: `<YYYY-MM-DD>`
- `all required boxes checked`: `<yes / no>`
- `if no, do not open the PR yet`: `<confirmed>`
