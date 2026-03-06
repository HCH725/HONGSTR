# HONGSTR Prototype Review Request Changes Note Template v1

Use this template when a reviewer needs to return a central steward shadow/prototype review package for changes.

This template standardizes reviewer-side `request changes` notes for governance review only.

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

## 1. Basic Information

| Field | Value |
|---|---|
| `review_id` | `<prototype-upgrade-review-YYYYMMDD or prototype-retirement-review-YYYYMMDD>` |
| `review_type` | `<upgrade / retirement>` |
| `reviewer` | `<name or handle>` |
| `review_author` | `<name or handle>` |
| `related_prs` | `<PR links>` |
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

If `other` is used, explain it explicitly:

- `<explanation>`

## 3. Required Fixes

Missing or insufficient evidence:

- `<what evidence is missing>`

Required template or checklist fixes:

- `<which template/checklist/decision record is missing or incomplete>`

Boundary rewrites or clarifications:

- `<which boundary statement must be rewritten>`

Observation window change:

- `<extend / complete / no change>`

PR split needed:

- `<yes/no>`

If `yes`, split guidance:

- `<what must move to a separate PR>`

## 4. Re-Review Conditions

Re-review may start only after all required conditions below are true.

- [ ] missing evidence has been added
- [ ] the correct review template is fully completed
- [ ] the evidence summary has been updated if needed
- [ ] author checklist is complete
- [ ] reviewer-facing boundary concerns are addressed
- [ ] rollout scope has been removed or split out
- [ ] observation window is complete, if that was the blocker

Kickoff SOP needs to be re-checked:

- `<yes / no>`

Evidence summary needs to be resubmitted:

- `<yes / no>`

Re-review note:

- `<what specifically must be true before re-review>`

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

- `<wait for resubmission / require PR split / require longer observation / stop review>`

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
| `request_changes_reasons` | `<selected reasons>` |
| `re-review_allowed_after_fixes` | `<yes / no>` |
| `rollout_mixed_in` | `<yes / no>` |
| `further_scope_split_required` | `<yes / no>` |
