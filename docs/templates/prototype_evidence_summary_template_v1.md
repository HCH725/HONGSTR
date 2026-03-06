# HONGSTR Prototype Evidence Summary Template v1

Use this template when a future author needs a standardized evidence summary for a central steward shadow/prototype review package.

This template is for evidence summary only.

It is not:

- a review decision by itself
- a rollout request
- a rollout approval
- a canonical state artifact

This template must not be used to change `/status`, `/daily`, or `/dashboard` truth sources.

## 0. How To Use

1. complete this template before or alongside the matching review template
2. use it for:
   - `upgrade review`
   - `retirement review`
   - `evidence review`, if a docs-only evidence review is opened
3. keep the filled output non-canonical and docs-only
4. do not treat a completed evidence summary as a rollout decision

Recommended companion docs:

- `docs/architecture/prototype_evidence_collection_plan_v1.md`
- `docs/templates/prototype_upgrade_review_template_v1.md`
- `docs/templates/prototype_retirement_review_template_v1.md`
- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- `docs/examples/prototype_review_package_example_v1.md`
- `docs/ops/prototype_review_package_naming_convention_v1.md`

## 1. Basic Information

| Field | Value |
|---|---|
| `prototype_id` | `central-steward-shadow-prototype` |
| `review_type` | `<upgrade-review / retirement-review / evidence-review>` |
| `review_window` | `<YYYY-MM-DD..YYYY-MM-DD>` |
| `review_author` | `<name or handle>` |
| `reviewer` | `<name or handle>` |
| `related_prs` | `<links or none>` |
| `related_docs` | `docs/architecture/prototype_evidence_collection_plan_v1.md`, `docs/architecture/prototype_retirement_criteria_v1.md`, `docs/ops/prototype_review_kickoff_sop_v1.md` |

## 2. Observation Summary

Complete every field. If a field is unavailable, write `unknown` and explain why.

| Evidence item | Observed value | Interpretation | Evidence source |
|---|---:|---|---|
| `shadow_summary_generation_frequency` | `<value>` | `<low / medium / high and why>` | `<log / note / audit>` |
| `dedupe_hit_rate` | `<value>` | `<useful / low-value / unstable>` | `<log / note / audit>` |
| `cooldown_hit_rate` | `<value>` | `<useful / low-value / unstable>` | `<log / note / audit>` |
| `recovery_of_ratio` | `<value>` | `<useful closure / churn / unclear>` | `<log / note / audit>` |
| `false_positive_noise` | `<value>` | `<low / medium / high and why>` | `<log / note / audit>` |
| `decision_value` | `<value>` | `<net-new context / low-value / unclear>` | `<review note>` |
| `canonical_overlap` | `<value>` | `<low / medium / high and why>` | `<comparison note>` |

## 3. Boundary Checks

Every row must be filled with evidence, not opinion.

| Boundary check | Pass / Fail | Evidence | Notes |
|---|---|---|---|
| `internal_only` still holds | `<pass/fail>` | `<evidence>` | `<note>` |
| `not_canonical` still holds | `<pass/fail>` | `<evidence>` | `<note>` |
| does not affect `/status` | `<pass/fail>` | `<evidence>` | `<note>` |
| does not affect `/daily` | `<pass/fail>` | `<evidence>` | `<note>` |
| does not affect `/dashboard` truth | `<pass/fail>` | `<evidence>` | `<note>` |
| does not write `data/state/*` | `<pass/fail>` | `<evidence>` | `<note>` |
| does not create a second state writer | `<pass/fail>` | `<evidence>` | `<note>` |
| does not touch bounded repair | `<pass/fail>` | `<evidence>` | `<note>` |
| does not change `tg_cp` runtime | `<pass/fail>` | `<evidence>` | `<note>` |

## 4. Evidence Sources

Mark every source actually used.

- [ ] `local/runtime log`
- [ ] `manual observation notes`
- [ ] `docs audit`
- [ ] `artifact inspection under approved non-canonical paths`
- [ ] `other approved source`: `<describe>`

Source notes:

- `<note 1>`
- `<note 2>`

Non-canonical reminder:

- this evidence summary must not be written into `data/state/*`
- this evidence summary must not be reused as canonical status
- this evidence summary must not back-fill `/status`, `/daily`, or `/dashboard`

## 5. Preliminary Assessment

Select one:

- `keep`
- `candidate for upgrade review`
- `candidate for retirement review`
- `insufficient evidence`

Current assessment:

`<selected status>`

Assessment rationale:

- `<reason 1>`
- `<reason 2>`
- `<reason 3>`

## 6. Next Action

Select one or more as needed:

- `continue observation`
- `open upgrade review`
- `open retirement review`
- `no action`

Next action detail:

- `<next step>`

## 7. Kill Switch / Rollback Note

Current kill switch:

- `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`

Rollback note:

- `<note>`

## 8. Non-Rollout Reminder

State explicitly:

- this evidence summary is not a review conclusion by itself
- this evidence summary is not rollout approval
- this evidence summary does not change canonical SSOT
- this evidence summary does not change `/status`, `/daily`, or `/dashboard`
