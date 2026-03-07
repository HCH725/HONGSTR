# HONGSTR Prototype Blocker Reference Explanatory-Inline Cue Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference explanatory-inline cue alignment PR
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

This record defines the canonical explanatory-inline cue phrases for non-live blocker-reference wording in the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Explanatory-Inline Cue Drift Found

The current docs had recurring drift in these patterns:

- some docs used `reminder prose` where the local meaning was simply explanatory, non-live wording
- some docs used `compact table cells` or `table-cell reminder` without a stable canonical cue phrase
- some docs used broad phrases such as `inline fragment` or `explanatory inline fragment` when the local meaning was specifically a bare placeholder fragment
- some docs did not explicitly contrast these non-live cues with `live blocker-evidence-reference field`, `live fill-in field`, and `live field block`

## 2. Drift To Canonical Mapping

| Drift / old cue wording | Canonical cue phrase | Notes |
|---|---|---|
| `reminder prose` | `explanatory prose` | Use for non-live wording that explains a rule rather than rendering a live field. |
| `table-cell reminder` or plural `compact table cells` | `compact table cell` | Use when the non-live explanation is compressed into one small table cell. |
| `inline fragment` or `explanatory inline fragment` | `inline placeholder-only fragment` | Use when the non-live wording is only the bare angle-bracket placeholder snippet. |
| prose that says inline is allowed without naming the non-live context | `explanatory prose` or `compact table cell` | Name the non-live context explicitly. |
| prose that cites only `<single link: ...>` or `<one-or-more links: ...>` without naming that shape | `inline placeholder-only fragment` | Keep the bare placeholder cue explicit. |

## 3. Canonical Explanatory-Inline Cue Phrases

Use these canonical explanatory-inline cue phrases:

- `explanatory prose`
- `compact table cell`
- `inline placeholder-only fragment`

Cue rule:

- use `explanatory prose` as the primary cue phrase for non-live blocker-reference explanation text
- use `compact table cell` when the non-live explanation is compressed into a compact tabular cell
- use `inline placeholder-only fragment` when the non-live wording is only the bare placeholder snippet, not a live field
- keep these cue phrases distinct from `live blocker-evidence-reference field`, `live fill-in field`, and `live field block`

Field split rule:

- explanatory-inline cue phrases are not blocker-evidence-reference labels
- explanatory-inline cue phrases are not blocker-reference field-caption formatting
- explanatory-inline cue phrases are not blocker-reference rendering rules
- explanatory-inline cue phrases are not blocker-reference live-field cue phrases
- explanatory-inline cue phrases are not blocker-reference-target hint labels
- explanatory-inline cue phrases are not blocker-reference multiplicity hint labels
- explanatory-inline cue phrases are not blocker-reference ordering hint labels
- explanatory-inline cue phrases are not blocker-reference applicability hint labels
- explanatory-inline cue phrases are not blocker-reference placeholder shapes

## 4. Legacy Aliases / Formats No Longer Recommended

These aliases or broad cue wordings should not be introduced in new or updated package docs as non-live blocker-reference cues:

- `reminder prose`
- `table-cell reminder`
- plural `compact table cells` when a single local cue is intended
- `inline fragment`
- `explanatory inline fragment`

These may remain in historical PR discussion or supporting prose, but not in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
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

- templates may mention all three canonical non-live cue phrases in one rule block
- checklists may use one reminder sentence that contrasts non-live cue phrases with live-field cue phrases
- examples may mention `inline placeholder-only fragment` inside `explanatory prose` or a `compact table cell`

Even with those thin variations:

- the canonical cue phrase itself should stay recognizable
- explanatory-inline cue phrases must not replace live-field cue phrases, field captions, evidence-reference labels, hint labels, placeholder-shape parts, or rendering rules
- explanatory-inline cue phrases must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Explanatory-inline cue alignment helps because:

- glossary, templates, and examples stop drifting between `reminder prose`, `table-cell reminder`, and `inline fragment` with no stable non-live cue set
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when non-live blocker-reference wording remains documentation-only
- Stage 7 read-only reporting stays clear because non-live cue phrases do not imply Telegram or runtime behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can copy one stable non-live cue set without re-litigating how to refer to explanatory-only wording versus the actual live field

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical blocker-reference explanatory-inline cue set so `explanatory prose`, `compact table cell`, and `inline placeholder-only fragment` stay fixed for non-live wording, while `live blocker-evidence-reference field`, `live fill-in field`, and `live field block` remain the canonical live-field cue set.
