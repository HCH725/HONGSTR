# HONGSTR Prototype Blocker Reference Live-Field Cue Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference live-field cue alignment PR
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

This record defines the canonical live-field cue phrases for blocker-evidence-reference fields in the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Live-Field Cue Drift Found

The current docs had recurring drift in these patterns:

- some docs used broad phrases such as `live field` or `actual field to fill` instead of one canonical cue phrase
- some docs alternated between `live blocker-evidence-reference entry` and `live blocker-evidence-reference field`
- some docs used `live fill-in field` and `live field block` without clearly stating that these are secondary cue phrases for different emphasis
- some rendering-rule reminders described the live object indirectly instead of using one stable cue phrase set

## 2. Drift To Canonical Mapping

| Drift / old cue wording | Canonical cue phrase | Notes |
|---|---|---|
| generic `live field` | `live blocker-evidence-reference field` | Use as the primary cue phrase for the actual blocker-proof field being discussed. |
| `live blocker-evidence-reference entry` | `live blocker-evidence-reference field` | Normalize entry-vs-field drift into one primary cue phrase. |
| `actual field to fill` or `fillable blocker-proof field` | `live fill-in field` | Use when the reminder needs to emphasize that the reader is expected to paste or retain a link. |
| `stacked live field` or `live stacked block` | `live field block` | Use when the reminder needs to emphasize the rendered stacked block form. |
| `live field form` when the local point is the expanded stacked rendering | `live field block` | Keep the rendered block cue stable. |

## 3. Canonical Live-Field Cue Phrases

Use these canonical live-field cue phrases:

- `live blocker-evidence-reference field`
- `live fill-in field`
- `live field block`

Cue rule:

- use `live blocker-evidence-reference field` as the primary cue phrase for the actual blocker-proof field under discussion
- use `live fill-in field` when the local sentence needs to emphasize that the field is the one the reader fills or updates
- use `live field block` when the local sentence needs to emphasize the rendered stacked block form of that live field
- keep these cue phrases stable instead of falling back to broad prose such as `live field`, `entry`, or `field form`

Field split rule:

- live-field cue phrases are not blocker-evidence-reference labels
- live-field cue phrases are not blocker-reference field-caption formatting
- live-field cue phrases are not blocker-reference rendering rules
- live-field cue phrases are not blocker-reference explanatory-inline cue phrases; those phrases are governed by `docs/ops/prototype_blocker_reference_explanatory_inline_cue_alignment_record_v1.md`
- live-field cue phrases are not blocker-reference live-vs-non-live contrast sentences; those sentences are governed by `docs/ops/prototype_blocker_reference_live_nonlive_contrast_alignment_record_v1.md`
- live-field cue phrases are not blocker-reference-target hint labels
- live-field cue phrases are not blocker-reference multiplicity hint labels
- live-field cue phrases are not blocker-reference ordering hint labels
- live-field cue phrases are not blocker-reference applicability hint labels
- live-field cue phrases are not blocker-reference placeholder shapes

## 4. Legacy Aliases / Formats No Longer Recommended

These aliases or broad cue wordings should not be introduced in new or updated package docs as live-field cues:

- generic `live field`
- `live blocker-evidence-reference entry`
- `actual field to fill`
- `fillable blocker-proof field`
- `live field form`
- `live stacked block`

These may remain in historical PR discussion or supporting prose, but not in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_blocker_reference_rendering_exception_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_field_caption_casing_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_placeholder_shape_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_applicability_hint_alignment_record_v1.md`
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

- templates may mention all three canonical cue phrases in one rule block
- checklists may use a single reminder sentence that keeps the three cue phrases recognizable
- examples may contrast explanatory inline snippets with a `live blocker-evidence-reference field` rendered as a `live field block`

Even with those thin variations:

- the canonical cue phrase itself should stay recognizable
- live-field cue phrases must not replace field captions, evidence-reference labels, hint labels, placeholder-shape parts, or rendering rules
- live-field cue phrases must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Live-field cue alignment helps because:

- glossary, templates, and examples stop drifting between `field`, `entry`, `fill-in field`, and `field block` with no stable cue hierarchy
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when blocker-proof field language remains documentation-only
- Stage 7 read-only reporting stays clear because live-field cue phrases do not imply Telegram or runtime behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can copy one stable cue set without re-litigating how to refer to the actual fillable blocker-proof field versus its rendered block form

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical blocker-reference live-field cue set so `live blocker-evidence-reference field` stays the primary cue phrase, `live fill-in field` is used when fillability needs emphasis, and `live field block` is used when the rendered stacked block form needs emphasis.
