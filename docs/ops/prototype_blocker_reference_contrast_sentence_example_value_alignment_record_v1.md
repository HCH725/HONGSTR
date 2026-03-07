# HONGSTR Prototype Blocker Reference Contrast Sentence Example-Value Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference contrast-sentence example-value alignment PR
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

This record defines the canonical short examples for live-vs-non-live contrast sentences in the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Contrast-Sentence Example-Value Drift Found

The current docs had recurring drift in these patterns:

- some docs used long rule prose as if it were the short example value
- some docs used a `Scope plus exclusion short example:` in one file but a `Placeholder location short example:` in another with no shared canonical example set
- some docs used lower-case short examples while others used full-sentence short examples
- some docs used a long combined example where one or two shorter canonical examples would be clearer

## 2. Drift To Canonical Mapping

| Drift / old example wording | Canonical short example | Notes |
|---|---|---|
| `in non-live context, treat non-live blocker-reference wording here as explanatory prose or a compact table cell; it is not a live fill-in field` | `In non-live context, this is not a live fill-in field.` | Use as the canonical `Scope plus exclusion short example:` value. |
| `use inline placeholder-only fragment only for the bare angle-bracket placeholder outside the live field block` | `Keep the bare placeholder outside the live field block.` | Use as the canonical `Placeholder location short example:` value. |
| `in non-live context, this is not a live fill-in field` | `In non-live context, this is not a live fill-in field.` | Normalize capitalization and terminal punctuation. |
| `in non-live context, this is not a live fill-in field. keep the bare placeholder outside the live field block.` | `In non-live context, this is not a live fill-in field. Keep the bare placeholder outside the live field block.` | Use as the canonical `Live versus non-live short example:` value. |
| long prose that inventories scope, exclusion, and placeholder location in one line | `In non-live context, this is not a live fill-in field. Keep the bare placeholder outside the live field block.` | Keep the example short and sentence-bounded. |

## 3. Canonical Short Examples

Use these canonical short examples:

- `Scope plus exclusion short example:` `In non-live context, this is not a live fill-in field.`
- `Placeholder location short example:` `Keep the bare placeholder outside the live field block.`
- `Live versus non-live short example:` `In non-live context, this is not a live fill-in field. Keep the bare placeholder outside the live field block.`

Example-value rule:

- use the `Scope plus exclusion short example:` value when the local point is non-live scope plus live-field exclusion
- use the `Placeholder location short example:` value when the local point is where the bare placeholder may appear
- use the `Live versus non-live short example:` value only when one local example needs both short examples together
- keep these short examples short; do not replace them with longer rule prose

Field split rule:

- contrast-sentence example values are not blocker-reference short-example block-intro phrases; those phrases are governed by `docs/ops/prototype_blocker_reference_short_example_block_intro_alignment_record_v1.md`
- contrast-sentence example values are not blocker-reference live-field cue phrases
- contrast-sentence example values are not blocker-reference explanatory-inline cue phrases
- contrast-sentence example values are not blocker-reference live-vs-non-live contrast sentences; those sentences are governed by `docs/ops/prototype_blocker_reference_live_nonlive_contrast_alignment_record_v1.md`
- contrast-sentence example values are not blocker-reference contrast-sentence combination rules; those rules are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_combination_rule_alignment_record_v1.md`
- contrast-sentence example values are not blocker-reference short-example placement rules; those rules are governed by `docs/ops/prototype_blocker_reference_short_example_label_placement_alignment_record_v1.md`
- contrast-sentence example values are not blocker-reference contrast-sentence punctuation/style rules; those rules are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_punctuation_style_alignment_record_v1.md`
- contrast-sentence example values are not blocker-reference short-example labels; those labels are governed by `docs/ops/prototype_blocker_reference_short_example_label_alignment_record_v1.md`

## 4. Legacy Examples No Longer Recommended

These older examples should not be introduced in new or updated package docs as canonical short examples:

- long rule prose used as if it were the example value
- lower-case example sentences without terminal punctuation
- one long example line that blends scope, exclusion, placeholder location, and rule commentary together

These may remain in historical PR discussion or drift tables, but not as active short examples in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_blocker_reference_contrast_sentence_combination_rule_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_live_nonlive_contrast_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_explanatory_inline_cue_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_live_field_cue_alignment_record_v1.md`
- `docs/templates/prototype_review_request_changes_note_template_v1.md`
- `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- `docs/templates/prototype_review_reviewer_checklist_v1.md`
- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- `docs/examples/prototype_review_package_example_v1.md`
- `docs/examples/prototype_resubmission_example_v1.md`
- `docs/ops/prototype_review_package_index_v1.md`

## 6. Very-Thin Variation Rule

Very-thin grammatical variation is allowed only when needed by the local structure:

- templates may show one or two canonical short-example values
- examples may show the `Live versus non-live short example:` value when both short examples are needed together
- placement of label-plus-value lines is governed by `docs/ops/prototype_blocker_reference_short_example_label_placement_alignment_record_v1.md`

Even with those thin variations:

- the canonical short example itself should stay recognizable
- block-intro wording is governed separately by `docs/ops/prototype_blocker_reference_short_example_block_intro_alignment_record_v1.md`
- example values must not replace contrast sentences, combination rules, live-field cue phrases, explanatory-inline cue phrases, rendering rules, field captions, evidence-reference labels, hint labels, or placeholder-shape parts
- example values must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Contrast-sentence example-value alignment helps because:

- glossary, templates, and examples stop drifting between long rule prose and short example sentences
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when contrast examples remain deterministic and small
- Stage 7 read-only reporting stays clear because these short examples do not imply Telegram or runtime behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can copy one stable short-example set instead of inventing fresh example prose for the same contrast rule

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical short-example set so `In non-live context, this is not a live fill-in field.`, `Keep the bare placeholder outside the live field block.`, and `In non-live context, this is not a live fill-in field. Keep the bare placeholder outside the live field block.` stay fixed wherever the docs need short contrast examples.
