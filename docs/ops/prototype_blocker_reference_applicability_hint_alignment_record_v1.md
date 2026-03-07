# HONGSTR Prototype Blocker Reference Applicability Hint Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference applicability hint alignment PR
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

This record defines the canonical blocker-reference applicability hint labels for the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Blocker-Reference Applicability Hint Drift Found

The current docs had recurring drift in these patterns:

- some blocker evidence-reference reminders used broad prose such as `the applicable ... fields` instead of one fixed applicability hint label
- some grouped blocker-proof examples used `as applicable` without saying whether the hint meant `if applicable`, `when requested`, or `only when closure proof exists`
- some evidence-reference notes implied that the governing note link might or might not appear, but did not use one canonical hint such as `if present`
- some closure-proof reminders described the condition in prose instead of using one normalized applicability hint for closure evidence

## 2. Drift To Canonical Mapping

| Drift / old applicability wording | Canonical applicability hint label | Notes |
|---|---|---|
| `the applicable ... fields` | `if applicable` | Use when the blocker evidence-reference field may remain blank without implying a missing blocker-proof obligation. |
| `as applicable` | `if applicable` | Normalize broad optionality prose into the canonical applicability hint. |
| `if that was requested` when used to decide whether a blocker evidence-reference field should be filled | `when requested` | Use when the blocker-proof field depends on an explicit reviewer request. |
| `if available` or `if already in the package` for a blocker note link | `if present` | Use when the blocker-proof link may already exist in the package and should be retained when present. |
| prose such as `once closure proof exists` or `when there is closure proof` | `only when closure proof exists` | Use when the closure evidence-reference field is relevant only after actual closure proof exists. |

## 3. Canonical Blocker-Reference Applicability Hint Labels

Use these canonical blocker-reference applicability hint labels:

- `if applicable`
- `when requested`
- `if present`
- `only when closure proof exists`

Field split rule:

- blocker-reference applicability hint labels are not blocker-evidence-reference labels
- blocker-reference applicability hint labels are not blocker-reference field-caption formatting; that formatting is governed by `docs/ops/prototype_blocker_reference_field_caption_casing_alignment_record_v1.md`
- blocker-reference applicability hint labels are not blocker-reference rendering rules; those rules are governed by `docs/ops/prototype_blocker_reference_rendering_exception_alignment_record_v1.md`
- blocker-reference applicability hint labels are not blocker-reference live-field cue phrases; those phrases are governed by `docs/ops/prototype_blocker_reference_live_field_cue_alignment_record_v1.md`
- blocker-reference applicability hint labels are not blocker-reference-target hint labels
- blocker-reference applicability hint labels are not blocker-reference multiplicity hint labels
- blocker-reference applicability hint labels are not blocker-reference ordering hint labels
- blocker-reference applicability hint labels are not blocker-reference placeholder shapes; those shapes are governed by `docs/ops/prototype_blocker_reference_placeholder_shape_alignment_record_v1.md`
- blocker-reference applicability hint labels are not blocker-closure-status labels

## 4. Legacy Aliases No Longer Recommended

These aliases should not be introduced in new or updated package docs as structured blocker-reference applicability hints:

- `the applicable ... fields`
- `as applicable`
- `if available`
- `if already in the package`
- closure-proof condition prose with no normalized applicability hint label

These may remain in historical PR discussion or supporting prose, but not in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_blocker_reference_ordering_hint_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_multiplicity_hint_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_target_hint_alignment_record_v1.md`
- `docs/ops/prototype_blocker_evidence_reference_alignment_record_v1.md`
- `docs/ops/prototype_review_package_index_v1.md`
- `docs/templates/prototype_review_request_changes_note_template_v1.md`
- `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- `docs/templates/prototype_review_reviewer_checklist_v1.md`
- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- `docs/examples/prototype_review_package_example_v1.md`
- `docs/examples/prototype_resubmission_example_v1.md`

## 6. Very-Thin Variation Rule

Very-thin grammatical variation is allowed only when needed by the local structure:

- templates may list the canonical applicability hint labels in one rule block
- checklists may mention the applicability hint labels inside a reminder sentence
- examples may describe the applicability hint labels next to grouped blocker evidence references

Even with those thin variations:

- the canonical applicability hint label itself should stay recognizable
- applicability hints must not replace blocker-evidence-reference labels, target hint labels, multiplicity hint labels, or ordering hint labels
- applicability hints must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Blocker-reference applicability hint alignment helps because:

- glossary, templates, and examples stop drifting between `applicable`, `as applicable`, `if available`, and other ad hoc optionality prose
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when blocker proof applicability remains documentation-only
- Stage 7 read-only reporting stays clear because applicability hints do not imply runtime or Telegram behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can point to optional versus required blocker proof consistently without re-litigating when a blocker evidence-reference field should be filled or left blank

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical blocker-reference applicability hint set so `if applicable`, `when requested`, `if present`, and `only when closure proof exists` stay consistent across glossary, templates, examples, and index docs, while blocker-evidence-reference labels, target hint labels, multiplicity hint labels, ordering hint labels, blocker-closure statuses, and reviewer response states remain separate glossary-defined fields.
