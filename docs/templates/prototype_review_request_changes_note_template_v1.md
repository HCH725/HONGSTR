# HONGSTR Prototype Review Request Changes Note Template v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / template-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype review request-changes note template PR
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

Use this template when a reviewer needs to return a central steward shadow/prototype review package for changes.

This template standardizes reviewer-side `request-changes notes` for governance review only.

It is not:

- rollout approval
- a final review decision record
- canonical state publication
- permission to change `/status`, `/daily`, or `/dashboard`

Use it when a review PR has not met the minimum bar for substantive approval or final decision recording.

## 0. How To Use

1. use this when the review package is incomplete, unclear, or mixed with forbidden scope
2. choose one or more fixed reason categories from the list below
3. state the required fixes concretely
4. state the re-review gate explicitly
5. stop the review if rollout drift or canonical-boundary erosion appears

If the package later reaches a real review conclusion, use:

- `docs/templates/prototype_review_decision_record_template_v1.md`

Before resubmitting after fixes, authors should complete `docs/templates/prototype_re_review_resubmission_checklist_v1.md`.
Authors may use `docs/examples/prototype_resubmission_example_v1.md` if they need a concrete resubmission flow example.

Reviewer response-state rule:

- this template is triggered by reviewer response state `request-changes note required`
- once the note is issued, the package remains in reviewer response state `return for fixes`
- after the listed conditions are satisfied, the reviewer may move the package to `re-review allowed after fixes`

Request-changes-reason rule:

- use the canonical reason labels exactly as listed below in structured fields
- treat phrases such as `missing evidence`, `boundary rewrite`, `rollout drift`, `canonical overlap not explained`, or `longer observation needed` as rationale or required-fix prose, not replacement reason labels

Required-fix label rule:

- use the canonical required-fix labels below when structuring blocker closure work:
  - `missing evidence added`
  - `template completed`
  - `boundary wording clarified`
  - `rollout wording removed`
  - `canonical overlap explanation added`
  - `observation window extended`

Blocker-closure-status rule:

- when blocker items are later tracked item-by-item in resubmission flow, use:
  - `completed`
  - `not completed`
  - `not applicable`
  - `unresolved`

Blocker-evidence-reference rule:

- when blocker proof is cited in this note or the later resubmission flow, use:
  - `closure evidence reference`
  - `fix evidence reference`
  - `review note reference`
  - `supporting evidence reference`

Blocker-reference-target hint rule:

- when the doc is hinting what kind of blocker-proof link should be pasted, use:
  - `PR comment link`
  - `evidence summary section link`
  - `template diff link`
  - `supporting doc link`

## 1. Basic Information

| Field | Value |
|---|---|
| `review_id` | `<prototype-upgrade-review-YYYYMMDD or prototype-retirement-review-YYYYMMDD>` |
| `review_type` | `<upgrade-review / retirement-review>` |
| `reviewer` | `<name or handle>` |
| `author` | `<name or handle>` |
| `related_prs` | `<PR links>` |
| `review note reference` | `<PR comment link>` |
| `supporting evidence reference` | `<supporting doc link>` |
| `related_docs` | `docs/templates/prototype_review_reviewer_checklist_v1.md`, `docs/templates/prototype_review_decision_record_template_v1.md`, `docs/ops/prototype_review_kickoff_sop_v1.md` |

## 2. Request-Changes Reason

Select one or more fixed reason categories:

- `insufficient evidence`
- `incomplete template`
- `boundary unclear`
- `rollout mixed into review PR`
- `canonical overlap unclear`
- `observation window incomplete`
- `other`

Selected reason(s):

- `<reason 1>`
- `<reason 2>`

Reason-split rule:

- `insufficient evidence` is a request-changes reason here; use assessment-status `needs more evidence` inside the evidence summary instead of reusing this reason label there
- `insufficient evidence` may also appear as a final decision outcome, but only in an explicit `decision outcome` field

If `other` is used, explain it explicitly:

- `<explanation>`

## 3. Required Fixes

`missing evidence added`:

- `<what evidence is missing>`

`template completed`:

- `<which template/checklist/decision record is missing or incomplete>`

`boundary wording clarified`:

- `<which boundary statement must be rewritten>`

`rollout wording removed`:

- `<which rollout wording must be removed or split out>`

`canonical overlap explanation added`:

- `<what canonical_overlap explanation must be added>`

`observation window extended`:

- `<extend / complete / no change>`

PR split needed:

- `<yes/no>`

If `yes`, split guidance:

- `<what must move to a separate PR>`

Fix evidence reference:

- `<evidence summary section link / template diff link>`

## 4. Re-Review Conditions

Re-review may start only after all required conditions below are true.

- [ ] `missing evidence added`
- [ ] `template completed`
- [ ] the evidence summary has been updated if needed
- [ ] author checklist is complete
- [ ] `boundary wording clarified`
- [ ] `rollout wording removed`
- [ ] `canonical overlap explanation added`, if that was the blocker
- [ ] `observation window extended`, if that was the blocker

Kickoff SOP needs to be re-checked:

- `<yes / no>`

Evidence summary needs to be resubmitted:

- `<yes / no>`

Closure evidence reference:

- `<supporting doc link>`

## 5. Kill Switch / Stop Condition

Stop review immediately when any of the following is true:

- rollout is mixed into the review PR
- canonical boundary is unclear or disputed
- the package tries to change `data/state/*`
- the package tries to change `src/hongstr/**`
- the package tries to change `scripts/refresh_state.sh`
- the package tries to change `scripts/state_snapshots.py`
- the package tries to change `tg_cp` runtime
- the package tries to introduce bounded repair or arbitrary execution

Current kill switch reminder:

- `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`

## 6. Reviewer Note

Request-changes summary:

- `<summary paragraph>`

Reviewer next step:

- `<wait for resubmission / require PR split / extend evidence window / stop review>`

## 7. Non-Rollout Reminder

State explicitly:

- this request-changes note is not rollout approval
- this request-changes note does not change canonical SSOT
- this request-changes note does not change `/status`, `/daily`, or `/dashboard`
- this request-changes note is only for prototype governance review

## 8. Reviewer Sign-Off

| Field | Value |
|---|---|
| `reviewer` | `<name or handle>` |
| `date` | `<YYYY-MM-DD>` |
| `request_changes_reason` | `<selected reason values>` |
| `reviewer_response_state_after_fixes` | `<re-review allowed after fixes / return for fixes>` |
| `rollout_mixed_in` | `<yes / no>` |
| `further_scope_split_required` | `<yes / no>` |
