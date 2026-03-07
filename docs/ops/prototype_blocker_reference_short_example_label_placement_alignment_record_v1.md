# HONGSTR Prototype Blocker Reference Short-Example Label Placement Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference short-example label placement alignment PR
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

This record defines the canonical placement rules for blocker-reference short-example labels in the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Short-Example Label Placement Drift Found

The current docs used a few different local renderings for the same canonical short-example labels:

- bullet-driven templates showed `label + example value` on one bullet line
- checklists showed the same `label + example value` on continuation lines under one governing bullet
- examples showed the full canonical set as a small example block with one standalone line per short example
- compact table cells named the canonical set, but should not expand the full three rendered short examples inside the cell

Those local patterns are acceptable only when they follow one explicit placement rule set. This PR makes that rule set canonical.

## 2. Drift To Canonical Mapping

| Drift / old placement | Canonical placement rule | Notes |
|---|---|---|
| label on one line, example value wrapped onto the next line | keep the label and example value on the same physical line | Keep the short example atomic and grep-friendly. |
| checklist child bullet rendered as another `-` item under one governing checklist bullet | use an indented continuation line under the governing bullet, with no second bullet marker | Use this in reviewer/author checklist follow-on reminders. |
| full three-example set packed into one compact table cell | compact table cell may reference the canonical set, but the full rendered trio belongs in an example block | Keep tables compact and readable. |
| slash-separated inline chain of multiple labeled short examples | one labeled line per short example; if the full trio is shown, use an example block | Avoid dense inline rendering. |
| example block with separate label line and separate value line | keep `label + example value` on one standalone line per short example | Do not split the atomic short-example pair. |
| bullet-driven template list with the label/value detached from the list item structure | keep each rendered short example as its own bullet line | Use this in request-changes note and re-review checklist style lists. |

## 3. Canonical Placement Rules

Use these canonical placement rules:

- keep the short-example label and example value on the same physical line whenever the short example is rendered
- in bullet-driven template lists, render each short example as its own bullet line
- in reviewer/author checklists, render short examples on indented continuation lines under the governing checklist bullet
- when the full canonical set is demonstrated, render it as an example block with one standalone labeled line per short example
- compact table cells may reference the canonical short-example set or placement rule, but should not render the full three labeled short examples in-cell
- if all three canonical short examples are shown together, prefer an example block over inline chaining or table-cell packing

Placement rule:

- same-line rendering is required for `Scope plus exclusion short example:`, `Placeholder location short example:`, and `Live versus non-live short example:`
- bullet continuation lines are for checklist follow-on reminders, not for sibling bullet items
- bullet list items are for template reminder lists where each short example is itself a sibling reminder
- example blocks are for demonstrations of the full canonical set or other multi-line example renderings
- compact table cells should summarize or point to the canonical set rather than display all rendered short examples

Field split rule:

- short-example placement rules are not short-example block-intro phrases; those phrases are governed by `docs/ops/prototype_blocker_reference_short_example_block_intro_alignment_record_v1.md`
- short-example placement rules are not short-example label wording; that wording is governed by `docs/ops/prototype_blocker_reference_short_example_label_alignment_record_v1.md`
- short-example placement rules are not short-example values; those values are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_example_value_alignment_record_v1.md`
- short-example placement rules are not contrast-sentence punctuation/style rules; those rules are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_punctuation_style_alignment_record_v1.md`
- short-example placement rules are not live-vs-non-live contrast sentences
- short-example placement rules are not live-field cue phrases or explanatory-inline cue phrases

## 4. Legacy Placement Styles No Longer Recommended

These old placement patterns should not be introduced in new or updated package docs as active short-example rendering:

- splitting the label and example value across separate lines
- using a second bullet marker where a continuation line is required
- stuffing the full three labeled short examples into one compact table cell
- chaining multiple labeled short examples in one slash-separated inline run
- removing the label from a standalone example line and leaving only plain prose

These may remain in historical PR discussion or drift tables, but not as active placement in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_blocker_reference_short_example_label_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_contrast_sentence_punctuation_style_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_contrast_sentence_example_value_alignment_record_v1.md`
- `docs/ops/prototype_review_package_index_v1.md`
- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- `docs/examples/prototype_review_package_example_v1.md`

Already conform; checked and left unchanged:

- `docs/templates/prototype_review_request_changes_note_template_v1.md`
- `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- `docs/templates/prototype_review_reviewer_checklist_v1.md`
- `docs/examples/prototype_resubmission_example_v1.md`

## 6. Very-Thin Variation Rule

Very-thin grammatical variation is allowed only when needed by the local structure:

- request-changes note and re-review checklist may keep each short example as its own bullet line
- reviewer and author checklists may keep short examples on continuation lines under one governing bullet
- examples may render the full canonical set as a three-line example block
- package-index or manifest table cells may reference the canonical set without expanding the full rendered trio

Even with those thin variations:

- each rendered short example must keep `label + example value` on the same line
- placement must not replace block-intro wording rules, label wording rules, example-value rules, punctuation/style rules, or contrast rules
- placement must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Short-example label placement alignment helps because:

- glossary, templates, and examples stop drifting between sibling bullet items, continuation lines, inline chains, and overpacked table cells
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when short-example placement remains deterministic and reviewable
- Stage 7 read-only reporting stays clear because these placement rules are documentation-only and do not imply Telegram or runtime behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can reuse one stable placement rule set without re-litigating where the same three canonical short examples should sit

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical short-example label placement rule set so `label + example value` stay on the same line, checklist follow-on reminders use continuation lines, bullet-driven templates use sibling bullet lines, full demonstrations use example blocks, and compact table cells stay reference-only instead of rendering the full trio.
