# HONGSTR Prototype Blocker Reference Contrast Sentence Combination Rule Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference contrast sentence combination-rule alignment PR
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

This record defines the canonical combination rules for live-vs-non-live contrast sentences in the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Contrast-Sentence Combination-Rule Drift Found

The current docs had recurring drift in these patterns:

- some docs combined `in non-live context`, `not a live fill-in field`, and `outside the live field block` into one long compound sentence
- some docs split `in non-live context` and `not a live fill-in field` into separate lines even when one short sentence needed both
- some checklist reminders listed all three contrast sentences without explaining when each one was actually needed
- some examples used a longer semicolon-heavy sentence where two short sentences were clearer

## 2. Drift To Canonical Mapping

| Drift / old combination wording | Canonical combination rule | Notes |
|---|---|---|
| one long sentence that combines `in non-live context`, `not a live fill-in field`, and `outside the live field block` | combine scope + exclusion in one short sentence, then keep placeholder-location contrast separate | Use two short sentences or two short rule lines once the third contrast point appears. |
| separate `in non-live context` and `not a live fill-in field` lines when one local reminder needs both | combine scope + exclusion in one short sentence | Keep the short combined sentence when the local point is simply non-live scope plus live-field exclusion. |
| checklist bullet that inventories all three contrast sentences without saying when each is needed | keep only the minimum necessary contrast sentence in checklist reminders | Checklists should remind, not restate every possible contrast sentence every time. |
| example prose with a semicolon-heavy contrast chain | prefer split short sentences once a third contrast point appears | Examples should demonstrate short readable rules, not dense compound prose. |

## 3. Canonical Combination Rules

Use these canonical contrast-sentence combination rules:

- `combine scope + exclusion in one short sentence when one local reminder must name both in non-live context and not a live fill-in field`
- `keep placeholder-location contrast as a separate short sentence when outside the live field block is the local point`
- `prefer split short sentences once a third contrast point would make the line compound`
- `keep only the minimum necessary contrast sentence in template, checklist, or example reminders`

Combination rule:

- combine `in non-live context` with `not a live fill-in field` only when one short sentence needs both the explanatory-inline scope and the live-field exclusion
- keep `outside the live field block` separate when the local point is the bare placeholder location rather than the general non-live scope
- split into two sentences or two short rule lines once adding the third contrast point would produce a long compound sentence
- in templates, checklists, and examples, keep only the minimum necessary contrast sentence for that local reminder instead of always repeating all three

Field split rule:

- contrast-sentence combination rules are not blocker-evidence-reference labels
- contrast-sentence combination rules are not blocker-reference field-caption formatting
- contrast-sentence combination rules are not blocker-reference rendering rules
- contrast-sentence combination rules are not blocker-reference live-field cue phrases
- contrast-sentence combination rules are not blocker-reference explanatory-inline cue phrases
- contrast-sentence combination rules are not blocker-reference live-vs-non-live contrast sentences; those sentences are governed by `docs/ops/prototype_blocker_reference_live_nonlive_contrast_alignment_record_v1.md`
- contrast-sentence combination rules are not blocker-reference contrast-sentence example values; those examples are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_example_value_alignment_record_v1.md`
- contrast-sentence combination rules are not blocker-reference-target hint labels
- contrast-sentence combination rules are not blocker-reference multiplicity hint labels
- contrast-sentence combination rules are not blocker-reference ordering hint labels
- contrast-sentence combination rules are not blocker-reference applicability hint labels
- contrast-sentence combination rules are not blocker-reference placeholder shapes

## 4. Legacy Aliases / Formats No Longer Recommended

These old sayings should not be introduced in new or updated package docs as contrast-sentence combination guidance:

- `just keep all three phrases in one line`
- `split every contrast phrase into its own line`
- long compound contrast reminders with no rule for when to split
- checklist reminders that repeat all three contrast sentences regardless of local need

These may remain in historical PR discussion or drift tables, but not as active combination-rule guidance in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_blocker_reference_live_nonlive_contrast_alignment_record_v1.md`
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

- templates may use two short rule lines instead of two prose sentences
- checklists may summarize the combination rule in one reminder bullet
- examples may demonstrate the combination rule by using one short scope+exclusion sentence plus one short placeholder-location sentence

Even with those thin variations:

- the canonical combination rule itself should stay recognizable
- combination rules must not replace contrast sentences, live-field cue phrases, explanatory-inline cue phrases, rendering rules, field captions, evidence-reference labels, hint labels, or placeholder-shape parts
- combination rules must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Contrast-sentence combination-rule alignment helps because:

- glossary, templates, and examples stop drifting between over-combined contrast prose and over-split reminder lines
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when contrast wording remains deterministic and small
- Stage 7 read-only reporting stays clear because these combination rules do not imply Telegram or runtime behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can copy one stable combination rule without re-litigating when to combine scope + exclusion and when to split out placeholder-location contrast

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical combination rule set so `in non-live context` plus `not a live fill-in field` may be combined into one short sentence when both points are needed together, while `outside the live field block` stays separate when the local point is the bare placeholder location, and templates/checklists/examples keep only the minimum necessary contrast sentence for that local reminder.
