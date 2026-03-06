# HONGSTR Prototype Required-Fix Alignment Record v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype request-changes required-fix label alignment PR
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

This record defines the canonical required-fix labels for the current prototype review/package docs.

This alignment is governance-only.

It does not:

- authorize rollout
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- authorize bounded repair
- change runtime wiring

## 1. Required-Fix Label Drift Found

The current docs had recurring drift in these patterns:

- request-changes notes and resubmission materials described required fixes with prose such as `missing evidence has been added`, `boundary wording rewritten`, `reviewer-facing boundary concerns are addressed`, or `observation window is complete`
- some fix descriptions overlapped with request-changes reasons, such as `missing evidence` or `remove rollout-oriented wording`, without a stable required-fix label
- `canonical_overlap` completion work appeared as prose rather than a recognizable fix-completion label
- observation-window follow-up drifted between `extend`, `complete`, and `longer observation` phrasing

## 2. Drift To Canonical Mapping

| Drift / old label | Canonical label | Notes |
|---|---|---|
| `missing evidence has been added` | `missing evidence added` | Keep the label short; detail belongs in the note body. |
| `filled the missing evidence` | `missing evidence added` | Normalize completion wording. |
| `the correct review template is fully completed` | `template completed` | Use the fix-completion label instead of restating the whole sentence. |
| `correct template/checklist/decision record is missing or incomplete` as a fix label | `template completed` | Keep the missing/incomplete detail in fix notes, not in the label. |
| `boundary wording rewritten` | `boundary wording clarified` | The fix goal is clarity, not the rewrite verb itself. |
| `reviewer-facing boundary concerns are addressed` | `boundary wording clarified` | Normalize broad prose to the canonical label. |
| `remove rollout-oriented wording` | `rollout wording removed` | Keep wording-removal detail in the fix note, not as the label itself. |
| `rollout scope has been removed or split out` | `rollout wording removed` | Split-out details may stay in notes, but the label should stay canonical. |
| `add missing canonical_overlap explanation` | `canonical overlap explanation added` | Normalize the concrete explanation fix. |
| `` `canonical_overlap` clarified `` | `canonical overlap explanation added` | Keep the fix label explicit. |
| `observation window is complete` | `observation window extended` | Normalize the blocker-closure label when more observation was required. |
| `longer observation window` | `observation window extended` | Keep the label tied to the completed fix. |

## 3. Canonical Required-Fix Labels

Use these canonical required-fix labels:

- `missing evidence added`
- `template completed`
- `boundary wording clarified`
- `rollout wording removed`
- `canonical overlap explanation added`
- `observation window extended`

Field split rule:

- required-fix label is not a request-changes reason
- required-fix label is not a reviewer response-state enum
- required-fix label is not a next-action enum
- `observation window extended` remains separate from next-action `extend evidence window`

## 4. Legacy Aliases No Longer Recommended

These aliases should not be introduced in new or updated package docs as structured required-fix labels:

- `missing evidence has been added`
- `filled the missing evidence`
- `boundary wording rewritten`
- `reviewer-facing boundary concerns are addressed`
- `remove rollout-oriented wording`
- `rollout scope has been removed or split out`
- `add missing canonical_overlap explanation`
- `` `canonical_overlap` clarified ``
- `observation window is complete`
- `longer observation window`

These may remain in historical PR discussion or supporting prose, but not in the normalized repo docs after this PR.

## 5. Files Aligned In This PR

Aligned:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/ops/prototype_request_changes_reason_alignment_record_v1.md`
- `docs/ops/prototype_review_package_index_v1.md`
- `docs/templates/prototype_review_request_changes_note_template_v1.md`
- `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- `docs/templates/prototype_review_reviewer_checklist_v1.md`
- `docs/examples/prototype_review_package_example_v1.md`
- `docs/examples/prototype_resubmission_example_v1.md`

## 6. Very-Thin Variation Rule

Very-thin grammatical variation is allowed only when needed by the local structure:

- prose may still describe the concrete fix details under each label
- checklists may mark a canonical label as completed or not completed
- examples may show the label in `request_changes_reason` follow-up snippets or fix-completion notes

Even with those thin variations:

- the canonical label itself should stay recognizable
- required-fix labels must not be merged into request-changes reasons
- required-fix labels must not be used as rollout or canonical-state language

## 7. Why This Alignment Helps

Required-fix label alignment helps because:

- glossary, templates, checklists, and examples stop drifting between fix-completion labels and prose-only descriptions
- Stage 2 single-writer and canonical-SSOT boundaries stay clearer when closure work remains documentation-only
- Stage 7 read-only reporting stays clear because fix-completion labels do not imply runtime or rollout behavior
- Stage 8 prototype/report-only posture remains explicit and pausable
- future PRs can discuss what was fixed without re-litigating whether `boundary wording rewritten` and `boundary wording clarified` are equivalent

## 8. Canonical Answer

Yes. The prototype review/package docs can and should use one canonical required-fix label set so `missing evidence added`, `template completed`, `boundary wording clarified`, `rollout wording removed`, `canonical overlap explanation added`, and `observation window extended` stay consistent across glossary, templates, examples, and index docs, while request-changes reasons, reviewer response states, and next actions remain separate glossary-defined fields.
