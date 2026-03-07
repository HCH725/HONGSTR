# HONGSTR Prototype Blocker Reference Rendering Exception Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference inline-vs-stacked rendering exception alignment PR
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

This record defines the canonical inline-vs-stacked rendering rules for blocker-evidence-reference fields in the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Blocker-Reference Rendering Drift Found

The current docs had recurring drift in these patterns:

- some docs treated inline `field: <...>` examples as if they were acceptable live blocker-evidence-reference field rendering
- some docs implied that a bare angle-bracket placeholder such as `<single link: ...>` could stand in for a full live field block
- some table or prose reminders used compact inline wording without saying that the compact form was explanatory only
- some placeholder-shape guidance and caption guidance did not explicitly say when a live field must expand to a stacked multi-line block

## 2. Drift To Canonical Mapping

| Drift / old rendering wording | Canonical rendering rule | Notes |
|---|---|---|
| `field: <...>` shown as if it were a live blocker-evidence-reference field | `stacked field block required for live blocker-evidence-reference fields` | Live fill-in fields use standalone caption lines plus the local hint lines. |
| bare `<single link: ...>` or `<one-or-more links: ...>` treated as the whole live field | `inline placeholder-only fragment allowed in explanatory prose` | Bare angle-bracket placeholders may appear only when the doc is describing the shape, not rendering the field itself. |
| prose or table reminder that says inline is fine without naming the condition | `compact inline form allowed only in reminder prose or compact table cells` | Compact inline form is explanatory only, not the default live field rendering. |
| local field block shows a caption or any `Applicability hint:` / `Ordering hint:` line but stays compressed to one line | `expand to multi-line block when field caption or hint lines are shown` | Once caption or hint lines are present, render the field as a stacked block. |
| grouped blocker-proof section uses several evidence-reference fields in one local sequence but leaves rendering style implicit | `stacked field block required for live blocker-evidence-reference fields` | Grouped blocker-proof fields should stay visibly separate and fillable. |

## 3. Canonical Rendering Rules

Use these canonical blocker-reference rendering rules:

- `inline placeholder-only fragment allowed in explanatory prose`
- `stacked field block required for live blocker-evidence-reference fields`
- `compact inline form allowed only in reminder prose or compact table cells`
- `expand to multi-line block when field caption or hint lines are shown`

Rendering rule:

- use stacked field blocks in templates and live example snippets where the reader is expected to fill or inspect a blocker-evidence-reference field
- allow compact inline form only when the doc is giving a reminder sentence, a compact table cell, or a drift-mapping example rather than rendering a live field
- if a field shows a standalone caption line or any `Applicability hint:` / `Ordering hint:` line, expand it to the canonical stacked multi-line block
- do not treat explanatory inline fragments as a substitute for live field rendering

Field split rule:

- blocker-reference rendering rules are not blocker-evidence-reference labels
- blocker-reference rendering rules are not blocker-reference field-caption formatting
- blocker-reference rendering rules are not blocker-reference-target hint labels
- blocker-reference rendering rules are not blocker-reference multiplicity hint labels
- blocker-reference rendering rules are not blocker-reference ordering hint labels
- blocker-reference rendering rules are not blocker-reference applicability hint labels
- blocker-reference rendering rules are not blocker-reference placeholder shapes

## 4. Legacy Aliases / Formats No Longer Recommended

These old renderings or sayings should not be introduced in new or updated package docs as blocker-reference rendering guidance:

- inline `field: <...>` shown as the default live field form
- bare angle-bracket placeholder treated as the complete live field
- `inline is fine` or similar wording without saying it is limited to explanatory prose or compact table cells
- compressed one-line field rendering after caption or hint lines have already been introduced

These may remain in historical PR discussion or drift tables, but not as active rendering guidance in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
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

- templates may state the canonical rendering rules inside one rule block
- checklists may mention the canonical rendering rules inside a reminder sentence
- examples may contrast explanatory inline fragments with live stacked field blocks

Even with those thin variations:

- the canonical rendering rule itself should stay recognizable
- rendering rules must not replace field captions, evidence-reference labels, hint labels, or placeholder-shape parts
- rendering rules must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Blocker-reference rendering-rule alignment helps because:

- glossary, templates, and examples stop drifting between explanatory inline snippets and live stacked field blocks
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when blocker-proof rendering remains documentation-only
- Stage 7 read-only reporting stays clear because rendering rules do not imply Telegram or runtime behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can copy one stable rendering rule without re-litigating when compact inline form is acceptable and when a live field must expand to a stacked block

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical blocker-reference rendering-rule set so inline placeholder-only fragments stay limited to explanatory prose, compact inline forms stay limited to reminder prose or compact table cells, and live blocker-evidence-reference fields expand to stacked multi-line blocks whenever field captions or hint lines are shown.
