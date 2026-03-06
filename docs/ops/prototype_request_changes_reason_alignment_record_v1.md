# HONGSTR Prototype Request-Changes Reason Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype request-changes-reason alignment PR
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

This record defines the canonical request-changes-reason labels for the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Request-Changes-Reason Drift Found

The current docs had recurring drift in these patterns:

- structured reason labels were canonical in the request-changes template, but nearby docs still used prose aliases such as `missing evidence`, `evidence gap`, `boundary rewrite`, or `rollout drift`
- reviewer and resubmission materials sometimes described the blocker in prose instead of restating the canonical reason label
- `insufficient evidence` risked being reused as assessment status, reviewer response state, and decision outcome without an explicit request-changes-reason split
- `canonical overlap` and observation-window blockers sometimes appeared as fix descriptions rather than recognizable reason labels

## 2. Drift To Canonical Mapping

| Drift / old label | Canonical label | Notes |
|---|---|---|
| `missing evidence` | `insufficient evidence` | Keep prose detail in fix notes, but use the canonical label in structured reason fields. |
| `evidence gap` | `insufficient evidence` | Use the canonical reason label instead of prose shorthand. |
| `template missing` | `incomplete template` | Use the normalized template-completeness label. |
| `template incomplete` | `incomplete template` | Normalize word order. |
| `boundary rewrite` | `boundary unclear` | The fix may be a rewrite, but the reason label is boundary clarity. |
| `ambiguous boundary wording` | `boundary unclear` | Normalize wording to the canonical label. |
| `rollout drift` | `rollout mixed into review PR` | Keep rollout-drift prose in notes if needed, but use the canonical reason label in structured fields. |
| `mixed rollout scope` | `rollout mixed into review PR` | Normalize to the review-PR-specific label. |
| `remove rollout-oriented wording` as a reason label | `rollout mixed into review PR` | Keep this as the required fix, not the reason label. |
| `canonical overlap not explained` | `canonical overlap unclear` | Normalize to the canonical label. |
| `add missing canonical_overlap explanation` as a reason label | `canonical overlap unclear` | Keep this as the required fix, not the reason label. |
| `longer observation needed` | `observation window incomplete` | Treat extra observation as the blocker label. |
| `observation incomplete` | `observation window incomplete` | Normalize wording to the canonical label. |

## 3. Canonical Request-Changes-Reason Labels

Use these canonical request-changes-reason labels:

- `insufficient evidence`
- `incomplete template`
- `boundary unclear`
- `rollout mixed into review PR`
- `canonical overlap unclear`
- `observation window incomplete`
- `other`

Field split rule:

- request-changes reason is not a reviewer response-state enum
- request-changes reason is not a next action enum
- `insufficient evidence` may also appear as a final decision outcome, but only when the field is explicitly `decision outcome`
- assessment-status `needs more evidence` remains separate from request-changes reason `insufficient evidence`

## 4. Legacy Aliases No Longer Recommended

These aliases should not be introduced in new or updated package docs as structured reason labels:

- `missing evidence`
- `evidence gap`
- `template missing`
- `template incomplete`
- `boundary rewrite`
- `ambiguous boundary wording`
- `rollout drift`
- `mixed rollout scope`
- `canonical overlap not explained`
- `longer observation needed`
- `observation incomplete`

These may remain in historical PR discussion or supporting prose, but not in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_reviewer_response_state_alignment_record_v1.md`
- `docs/ops/prototype_review_package_index_v1.md`
- `docs/templates/prototype_review_request_changes_note_template_v1.md`
- `docs/templates/prototype_review_reviewer_checklist_v1.md`
- `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- `docs/templates/prototype_review_decision_record_template_v1.md`
- `docs/examples/prototype_review_package_example_v1.md`
- `docs/examples/prototype_resubmission_example_v1.md`

## 6. Very-Thin Variation Rule

Very-thin grammatical variation is allowed only when needed by the local structure:

- prose may still describe the concrete fix, such as adding evidence or rewriting a boundary statement
- examples may use field labels such as `request_changes_reason`
- checklists may remind authors or reviewers to map blockers back to the canonical labels

Even with those thin variations:

- the canonical label itself should stay recognizable
- request-changes reasons must not be merged into reviewer response states
- request-changes reasons must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Request-changes-reason alignment helps because:

- glossary, templates, and examples stop drifting between structured blocker labels and freeform prose
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when request-changes blockers remain documentation-only
- Stage 7 read-only reporting stays clear because blocker labels do not imply runtime or rollout behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can discuss why a package was returned without re-litigating whether `missing evidence`, `evidence gap`, and `insufficient evidence` are equivalent

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical request-changes-reason set so `insufficient evidence`, `incomplete template`, `boundary unclear`, `rollout mixed into review PR`, `canonical overlap unclear`, `observation window incomplete`, and `other` stay consistent across glossary, templates, examples, and index docs, while reviewer response states, assessment status, decision outcome, and next action remain separate glossary-defined fields.
