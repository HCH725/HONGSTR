# HONGSTR Prototype Blocker Reference Field Caption Casing Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference field-caption casing alignment PR
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

This record defines the canonical blocker-reference field-caption formatting for the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Blocker-Reference Field-Caption Drift Found

The current docs had recurring drift in these patterns:

- some caption examples still described old lowercase forms such as `review note reference:`
- some examples and record text blurred the difference between the underlying evidence-reference label and the displayed caption formatting
- some local guidance implied the caption could appear without a trailing colon
- some older prose suggested inline or abbreviated caption forms instead of one fixed displayed caption

## 2. Drift To Canonical Mapping

| Drift / old field-caption formatting | Canonical field-caption formatting | Notes |
|---|---|---|
| `review note reference:` | `Review note reference:` | Use sentence case with an initial capital and trailing colon. |
| `closure evidence reference:` | `Closure evidence reference:` | Keep the same sentence-case rule with a trailing colon. |
| `fix evidence reference:` | `Fix evidence reference:` | Keep the same sentence-case rule with a trailing colon. |
| `supporting evidence reference:` | `Supporting evidence reference:` | Keep the same sentence-case rule with a trailing colon. |
| caption shown without trailing `:` | canonical caption plus trailing `:` | The displayed field caption keeps the colon in stacked field blocks. |
| abbreviated forms such as `review note ref:` or `supporting evidence ref:` | full canonical caption | Do not abbreviate blocker-reference field captions. |

## 3. Canonical Field Captions

Use these canonical blocker-reference field captions:

- `Review note reference:`
- `Closure evidence reference:`
- `Fix evidence reference:`
- `Supporting evidence reference:`

Formatting rule:

- use sentence case, not title case
- capitalize the first word only
- keep the trailing colon
- do not abbreviate or shorten the caption
- do not wrap the displayed caption line in backticks

Field split rule:

- blocker-reference field captions are not blocker-evidence-reference labels
- blocker-reference field captions are not blocker-reference rendering rules; those rules are governed by `docs/ops/prototype_blocker_reference_rendering_exception_alignment_record_v1.md`
- blocker-reference field captions are not blocker-reference live-field cue phrases; those phrases are governed by `docs/ops/prototype_blocker_reference_live_field_cue_alignment_record_v1.md`
- blocker-reference field captions are not blocker-reference explanatory-inline cue phrases; those phrases are governed by `docs/ops/prototype_blocker_reference_explanatory_inline_cue_alignment_record_v1.md`
- blocker-reference field captions are not blocker-reference live-vs-non-live contrast sentences; those sentences are governed by `docs/ops/prototype_blocker_reference_live_nonlive_contrast_alignment_record_v1.md`
- blocker-reference field captions are not blocker-reference-target hint labels
- blocker-reference field captions are not blocker-reference multiplicity hint labels
- blocker-reference field captions are not blocker-reference ordering hint labels
- blocker-reference field captions are not blocker-reference applicability hint labels
- blocker-reference field captions are not blocker-reference placeholder shapes

## 4. Legacy Aliases / Formats No Longer Recommended

These aliases or formats should not be introduced in new or updated package docs as displayed blocker-reference field captions:

- `review note reference:`
- `closure evidence reference:`
- `fix evidence reference:`
- `supporting evidence reference:`
- caption lines without a trailing colon
- abbreviated forms such as `review note ref:` or `supporting evidence ref:`

These may remain in historical PR discussion or supporting prose, but not in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
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

- templates may list the canonical field captions inside one rule block
- checklists may mention the canonical field captions inside a reminder sentence
- examples may mirror the same canonical field captions inside code fences

Even with those thin variations:

- the canonical field caption itself should stay recognizable
- field-caption formatting must not replace blocker-evidence-reference labels or any hint-label layer
- field-caption formatting must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Blocker-reference field-caption alignment helps because:

- glossary, templates, and examples stop drifting between lowercase caption text, missing-colon text, and the canonical displayed field-caption form
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when displayed field captions remain documentation-only
- Stage 7 read-only reporting stays clear because caption formatting does not imply runtime or Telegram behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can copy one stable caption format without re-litigating case, punctuation, or abbreviation rules

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical blocker-reference field-caption set so `Review note reference:`, `Closure evidence reference:`, `Fix evidence reference:`, and `Supporting evidence reference:` stay consistent across glossary, templates, examples, and index docs, while blocker-evidence-reference labels, target hint labels, multiplicity hint labels, ordering hint labels, applicability hint labels, and placeholder shapes remain separate glossary-defined layers.
