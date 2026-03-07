# HONGSTR Prototype Blocker Reference Short-Example Label Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference short-example label wording alignment PR
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

This record defines the canonical label wording used before blocker-reference contrast-sentence short examples in the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Short-Example Label Drift Found

The current docs had recurring drift in these patterns:

- some docs used `scope + exclusion` instead of the fixed word `plus`
- some docs used `live vs non-live` instead of the fixed word `versus`
- some docs used lower-case or parenthetical `canonical short example (...)` label forms
- some docs omitted `short example` from the label and treated the label as if it were the example value or punctuation/style rule

Most active templates/examples were already on the canonical label wording. The remaining drift was concentrated in glossary/record wording and package-index navigation.

## 2. Drift To Canonical Mapping

| Drift / old label wording | Canonical short-example label wording | Notes |
|---|---|---|
| `scope + exclusion short example:` | `Scope plus exclusion short example:` | Use `plus`, not `+`, and keep sentence-case label formatting. |
| `Canonical short example (scope + exclusion):` | `Scope plus exclusion short example:` | Remove parenthetical type tags and keep the canonical label itself stable. |
| `placeholder-location short example:` | `Placeholder location short example:` | Remove the hyphenated category spelling in active labels. |
| `canonical short example (placeholder location):` | `Placeholder location short example:` | Remove lower-case generic lead-in and parentheses. |
| `live-vs-non-live short example:` | `Live versus non-live short example:` | Use `versus`, not `vs`, and keep the label fully spelled out. |
| `canonical short example (live vs non-live):` | `Live versus non-live short example:` | Remove lower-case generic lead-in, parentheses, and `vs`. |
| label variants without `short example` | same label with `short example` included | Keep the label purpose explicit. |
| same label without a trailing colon | same label with a trailing colon | Keep the label formatting deterministic. |

## 3. Canonical Short-Example Labels

Use these canonical short-example labels:

- `Scope plus exclusion short example:`
- `Placeholder location short example:`
- `Live versus non-live short example:`

Label wording rule:

- use `plus`, not `+`
- use `versus`, not `vs`
- keep `short example` in every canonical label
- keep the trailing colon
- keep the label outside the backticked example value

Field split rule:

- short-example labels are not the short-example values themselves; those values are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_example_value_alignment_record_v1.md`
- short-example labels are not contrast-sentence punctuation/style rules; those rules are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_punctuation_style_alignment_record_v1.md`
- short-example labels are not contrast-sentence combination rules; those rules are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_combination_rule_alignment_record_v1.md`
- short-example labels are not live-vs-non-live contrast sentences; those sentences are governed by `docs/ops/prototype_blocker_reference_live_nonlive_contrast_alignment_record_v1.md`
- short-example labels are not live-field cue phrases or explanatory-inline cue phrases

## 4. Legacy Labels No Longer Recommended

These old label forms should not be introduced in new or updated package docs as active short-example labels:

- `scope + exclusion short example:`
- `live-vs-non-live short example:`
- `live vs non-live short example:`
- `canonical short example (...)`
- label lines that omit `short example`
- label lines that drop the trailing colon

These may remain in historical PR discussion or drift tables, but not as active label wording in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_blocker_reference_contrast_sentence_punctuation_style_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_contrast_sentence_example_value_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_contrast_sentence_combination_rule_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_live_nonlive_contrast_alignment_record_v1.md`
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

- templates may show one or two labeled short examples
- examples may show all three labeled short examples when demonstrating the full canonical set
- checklists may keep the label on a continuation line under one governing rule bullet

Even with those thin variations:

- the canonical label wording itself should stay recognizable
- label wording must not replace the example value, punctuation/style rule, combination rule, live-field cue wording, or explanatory-inline cue wording
- label wording must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Short-example label wording alignment helps because:

- glossary, records, templates, and examples stop drifting between `plus` and `+`, and between `versus` and `vs`
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when example labels remain deterministic and easy to grep
- Stage 7 read-only reporting stays clear because these labels are documentation-only and do not imply Telegram or runtime behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can reuse one stable label vocabulary without re-litigating how to caption the same three canonical short examples

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical blocker-reference short-example label vocabulary so `Scope plus exclusion short example:`, `Placeholder location short example:`, and `Live versus non-live short example:` stay fixed wherever those canonical short examples are shown.
