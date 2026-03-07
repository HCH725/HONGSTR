# HONGSTR Prototype Blocker Reference Short-Example Block-Intro Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference short-example block-intro wording alignment PR
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

This record defines the canonical intro phrases used before blocker-reference short-example blocks in the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Short-Example Block-Intro Drift Found

The current docs had recurring drift in these patterns:

- a normative record used `Use these canonical short examples:` while example/demo contexts sometimes used no intro phrase at all
- one example reminder used lower-case `keep the canonical short examples stable:`
- some local renderings risked treating the intro phrase as interchangeable with label wording, placement rules, or example values

The repo only needs a small fixed set of intro phrases, with context deciding which one applies.

## 2. Drift To Canonical Mapping

| Drift / old intro wording | Canonical intro phrase | Notes |
|---|---|---|
| no intro phrase before a standalone three-line short-example demonstration | `Example block:` | Use when the docs open a dedicated standalone example block. |
| `keep the canonical short examples stable:` | `Keep the canonical short examples stable:` | Keep the imperative phrase capitalized and keep the trailing colon. |
| ad hoc generic intros such as `canonical short examples:` or `short examples:` | `Use these canonical short examples:` | Use for normative glossary/record sections that introduce the canonical set itself. |
| same intro phrase without a trailing colon | same intro phrase with a trailing colon | Keep the block intro deterministic. |

## 3. Canonical Block-Intro Phrases

Use these canonical block-intro phrases:

- `Use these canonical short examples:`
- `Keep the canonical short examples stable:`
- `Example block:`

Block-intro rule:

- use imperative phrasing
- keep the trailing colon
- do not use synonym replacement such as `vs`, `here are`, `canonical examples`, or other ad hoc lead-ins
- use `Use these canonical short examples:` in glossary/record sections that define the canonical set
- use `Keep the canonical short examples stable:` in example/checklist reminder prose that tells the reader to preserve the fixed set
- use `Example block:` only when opening a standalone demonstration block that renders the canonical short examples directly
- if a template/checklist only needs local short-example lines under an existing governing bullet, do not invent a new intro phrase; let the governing bullet serve as the local intro

Field split rule:

- short-example block-intro phrases are not short-example label wording; that wording is governed by `docs/ops/prototype_blocker_reference_short_example_label_alignment_record_v1.md`
- short-example block-intro phrases are not short-example placement rules; those rules are governed by `docs/ops/prototype_blocker_reference_short_example_label_placement_alignment_record_v1.md`
- short-example block-intro phrases are not short-example values; those values are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_example_value_alignment_record_v1.md`
- short-example block-intro phrases are not contrast-sentence punctuation/style rules; those rules are governed by `docs/ops/prototype_blocker_reference_contrast_sentence_punctuation_style_alignment_record_v1.md`
- short-example block-intro phrases are not live-vs-non-live contrast sentences or cue phrases

## 4. Legacy Intro Wording No Longer Recommended

These old intro forms should not be introduced in new or updated package docs as active short-example block intros:

- no intro phrase before a standalone demonstration block
- lower-case `keep the canonical short examples stable:`
- ad hoc generic intros such as `canonical short examples:` or `short examples:`
- intro lines that drop the trailing colon

These may remain in historical PR discussion or drift tables, but not as active intro wording in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_blocker_reference_short_example_label_placement_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_short_example_label_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_contrast_sentence_punctuation_style_alignment_record_v1.md`
- `docs/ops/prototype_blocker_reference_contrast_sentence_example_value_alignment_record_v1.md`
- `docs/ops/prototype_review_package_index_v1.md`
- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- `docs/examples/prototype_review_package_example_v1.md`
- `docs/examples/prototype_resubmission_example_v1.md`

Already conform; checked and left unchanged:

- `docs/templates/prototype_review_request_changes_note_template_v1.md`
- `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- `docs/templates/prototype_review_reviewer_checklist_v1.md`

## 6. Very-Thin Variation Rule

Very-thin grammatical variation is allowed only when needed by the local structure:

- glossary/record sections may use `Use these canonical short examples:` before the normative three-line set
- example/checklist reminder prose may use `Keep the canonical short examples stable:` before a preserved three-line set
- standalone example demonstrations may use `Example block:` immediately before the rendered block
- templates/checklists with no standalone block-intro line may rely on the governing bullet instead of adding a new synonym intro

Even with those thin variations:

- the canonical intro phrase itself should stay recognizable
- intro wording must not replace label wording, placement rules, example values, or punctuation/style rules
- intro wording must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Short-example block-intro alignment helps because:

- glossary, records, and examples stop drifting between implicit intros, lower-case reminders, and ad hoc lead-ins
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when short-example guidance remains deterministic and grep-friendly
- Stage 7 read-only reporting stays clear because these intro phrases are documentation-only and do not imply Telegram or runtime behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can reuse one stable intro vocabulary without re-litigating how to open the same short-example blocks

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical short-example block-intro set so `Use these canonical short examples:`, `Keep the canonical short examples stable:`, and `Example block:` stay fixed by context, with no ad hoc synonym drift.
