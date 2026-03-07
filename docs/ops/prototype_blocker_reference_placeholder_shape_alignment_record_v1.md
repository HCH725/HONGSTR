# HONGSTR Prototype Blocker Reference Placeholder Shape Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference placeholder-shape alignment PR
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

This record defines the canonical blocker-reference placeholder shapes for the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Blocker-Reference Placeholder-Shape Drift Found

The current docs had recurring drift in these patterns:

- some blocker evidence-reference placeholders were rendered inline as `field: <...>` while others used stacked field blocks
- some field blocks showed the angle-bracket placeholder only, without the matching `Applicability hint:` or `Ordering hint:` line
- some files embedded applicability or ordering guidance in prose instead of keeping those hints in dedicated placeholder-shape lines
- some table cells mixed field meaning and placeholder formatting instead of using one recognizable placeholder shape

## 2. Drift To Canonical Mapping

| Drift / old placeholder shape | Canonical placeholder shape | Notes |
|---|---|---|
| `review note reference: <single link: ...>` | `Review note reference:` + `Applicability hint: ...` + `Ordering hint: ...` + `<single link: ...>` | Normalize inline field-plus-placeholder rendering into the canonical stacked shape. |
| field block with `<one-or-more links: ...>` but no `Applicability hint:` line | `Applicability hint: ...` + `<one-or-more links: ...>` | Keep applicability as its own line instead of hiding it in surrounding prose. |
| field block with `Applicability hint:` but no `Ordering hint:` line | `Applicability hint: ...` + `Ordering hint: ...` + `<...>` | Keep grouped blocker-proof order visible in the same local block. |
| prose sentence carrying ordering/applicability guidance next to a field block | dedicated `Applicability hint: ...` and `Ordering hint: ...` lines | Normalize prose-only guidance into the canonical placeholder-shape lines. |
| table-cell placeholder that mixes shape and field description | dedicated field block or compact field row using the same stacked placeholder parts in order | Keep the placeholder parts recognizable even if the local markdown structure is a table or example block. |

## 3. Canonical Placeholder Shape Specification

Use these canonical blocker-reference placeholder-shape components:

- `<single link: ...>`
- `<multiple links: ...>`
- `<one-or-more links: ...>`
- `Applicability hint: ...`
- `Ordering hint: ...`

Canonical stacked placeholder shape:

1. field label on its own line, ending with `:`
2. `Applicability hint: ...`
3. `Ordering hint: ...`
4. angle-bracket placeholder line such as `<single link: ...>`

Field split rule:

- placeholder shapes are not blocker-evidence-reference labels
- placeholder shapes are not blocker-reference-target hint labels
- placeholder shapes are not blocker-reference multiplicity hint labels
- placeholder shapes are not blocker-reference ordering hint labels
- placeholder shapes are not blocker-reference applicability hint labels

## 4. Legacy Aliases No Longer Recommended

These shapes should not be introduced in new or updated package docs as structured blocker-reference placeholders:

- inline `field: <...>` shapes when the surrounding doc already uses stacked field blocks
- field blocks that omit `Applicability hint:` or `Ordering hint:` while still relying on those semantics
- prose-only applicability or ordering guidance next to a blocker evidence-reference field
- mixed table-cell formatting that makes the canonical placeholder parts hard to recognize

These may remain in historical PR discussion or supporting prose, but not in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
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

- templates may show the canonical placeholder-shape parts in stacked field blocks
- checklists may mention the placeholder-shape parts inside a reminder sentence
- examples may mirror the stacked field blocks inside code fences

Even with those thin variations:

- the canonical placeholder-shape parts should stay recognizable
- placeholder shapes must not replace blocker-evidence-reference labels or any hint-label layer
- placeholder shapes must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Blocker-reference placeholder-shape alignment helps because:

- glossary, templates, and examples stop drifting between inline placeholders, partial field blocks, and prose-only guidance
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when blocker proof formatting remains documentation-only
- Stage 7 read-only reporting stays clear because placeholder shapes do not imply runtime or Telegram behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can copy one stable placeholder shape without re-litigating where `Applicability hint:`, `Ordering hint:`, and `<...>` belong

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical blocker-reference placeholder shape so `Applicability hint: ...`, `Ordering hint: ...`, and `<single link: ...>` / `<multiple links: ...>` / `<one-or-more links: ...>` stay consistent across glossary, templates, examples, and index docs, while blocker-evidence-reference labels, target hint labels, multiplicity hint labels, ordering hint labels, and applicability hint labels remain separate glossary-defined layers.
