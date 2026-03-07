# HONGSTR Prototype Blocker Reference Live-vs-Non-Live Contrast Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference live-vs-non-live contrast sentence alignment PR
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

This record defines the canonical contrast sentences used to distinguish live blocker-evidence-reference fields from non-live / explanatory-inline blocker-reference wording in the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Live-vs-Non-Live Contrast Drift Found

The current docs had recurring drift in these patterns:

- some docs said `not as a live fill-in field` instead of using one direct canonical contrast sentence
- some docs used `in that non-live context`, `compressed non-live reminder context`, or similar variants instead of one stable non-live scope sentence
- some docs used `outside the live field block` while others kept the same idea implicit
- some docs mixed contrast sentences with live-field cue phrases, explanatory-inline cue phrases, or rendering rules

## 2. Drift To Canonical Mapping

| Drift / old contrast wording | Canonical contrast sentence | Notes |
|---|---|---|
| `not as a live fill-in field` | `not a live fill-in field` | Use the direct contrast sentence when the local point is that non-live wording must not be treated as fillable live input. |
| `in that non-live context` | `in non-live context` | Remove filler words so the scope sentence stays stable. |
| `compressed non-live reminder context` or similar prose | `in non-live context` | Keep the scope sentence deterministic instead of varying by local prose. |
| prose that implies the bare placeholder must stay outside the live field area | `outside the live field block` | Use when the local point is that the bare placeholder snippet is not part of the stacked live field block. |
| mixed long-form contrast prose that combines scope and exclusion without a stable sentence | `not a live fill-in field` / `in non-live context` / `outside the live field block` | Split the contrast into the canonical sentence parts instead of inventing new prose. |

## 3. Canonical Contrast Sentences

Use these canonical live-vs-non-live contrast sentences:

- `not a live fill-in field`
- `outside the live field block`
- `in non-live context`

Contrast rule:

- use `not a live fill-in field` when the local sentence must explicitly exclude non-live blocker-reference wording from live fillability
- use `outside the live field block` when the local sentence must explicitly exclude the bare placeholder snippet from the stacked live field block
- use `in non-live context` when the local sentence must name the explanatory-inline scope
- keep these contrast sentences stable instead of falling back to ad hoc prose such as `not as a live fill-in field` or `in that non-live context`

Field split rule:

- live-vs-non-live contrast sentences are not blocker-evidence-reference labels
- live-vs-non-live contrast sentences are not blocker-reference field-caption formatting
- live-vs-non-live contrast sentences are not blocker-reference rendering rules
- live-vs-non-live contrast sentences are not blocker-reference live-field cue phrases; those phrases are governed by `docs/ops/prototype_blocker_reference_live_field_cue_alignment_record_v1.md`
- live-vs-non-live contrast sentences are not blocker-reference explanatory-inline cue phrases; those phrases are governed by `docs/ops/prototype_blocker_reference_explanatory_inline_cue_alignment_record_v1.md`
- live-vs-non-live contrast sentences are not blocker-reference contrast-sentence combination rules; those rules are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_combination_rule_alignment_record_v1.md`
- live-vs-non-live contrast sentences are not blocker-reference contrast-sentence example values; those examples are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_example_value_alignment_record_v1.md`
- live-vs-non-live contrast sentences are not blocker-reference contrast-sentence punctuation/style rules; those rules are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_punctuation_style_alignment_record_v1.md`
- live-vs-non-live contrast sentences are not blocker-reference-target hint labels
- live-vs-non-live contrast sentences are not blocker-reference multiplicity hint labels
- live-vs-non-live contrast sentences are not blocker-reference ordering hint labels
- live-vs-non-live contrast sentences are not blocker-reference applicability hint labels
- live-vs-non-live contrast sentences are not blocker-reference placeholder shapes

## 4. Legacy Aliases / Formats No Longer Recommended

These old sayings should not be introduced in new or updated package docs as live-vs-non-live contrast sentences:

- `not as a live fill-in field`
- `in that non-live context`
- `compressed non-live reminder context`
- long mixed contrast prose that does not use any canonical sentence part

These may remain in historical PR discussion or drift tables, but not as active contrast wording in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_blocker_reference_explanatory_inline_cue_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_live_field_cue_alignment_record_v1.md`
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

- templates may use the canonical contrast sentences while following `docs/ops/prototype_blocker_reference_contrast_sentence_combination_rule_alignment_record_v1.md`
- checklists may use one reminder sentence that contrasts the non-live cue set with live-field cue phrases
- examples may use `outside the live field block` when they are reminding the reader where the bare placeholder snippet may appear, while following the canonical combination rule

Even with those thin variations:

- the canonical contrast sentence itself should stay recognizable
- contrast sentences must not replace live-field cue phrases, explanatory-inline cue phrases, rendering rules, field captions, evidence-reference labels, hint labels, or placeholder-shape parts
- contrast sentences must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Live-vs-non-live contrast alignment helps because:

- glossary, templates, and examples stop drifting between `not as a live fill-in field`, `in that non-live context`, and other one-off contrast prose
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when live-vs-non-live wording remains deterministic and documentation-only
- Stage 7 read-only reporting stays clear because these contrast sentences do not imply Telegram or runtime behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can copy one stable contrast set without re-litigating how to distinguish live fillable fields from explanatory-inline reminder text

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical blocker-reference live-vs-non-live contrast set so `not a live fill-in field`, `outside the live field block`, and `in non-live context` stay fixed whenever the docs directly compare live blocker-evidence-reference fields with explanatory-inline wording.
