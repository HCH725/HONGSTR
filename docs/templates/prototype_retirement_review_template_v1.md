# HONGSTR Prototype Retirement Review Template v1

Use this template only for a future `retirement review` of the central steward shadow/prototype path.

Before opening a review PR, satisfy `docs/ops/prototype_review_kickoff_sop_v1.md`.
Authors should also complete `docs/templates/prototype_review_pr_author_checklist_v1.md` before opening the PR.
Authors may use `docs/examples/prototype_review_package_example_v1.md` as a package assembly example.
Authors should follow `docs/ops/prototype_review_package_naming_convention_v1.md` for review package titles and attachment names.

Do not use this template for rollout.

Do not use this template for upgrade review. Use `docs/templates/prototype_upgrade_review_template_v1.md` instead.

## 0. Review Start Rule

Start this template only when:

- the evidence collection window has completed and points toward low value, high overlap, high noise, or boundary erosion
- or a governance reviewer decides the prototype should be evaluated for archive/removal

Filled by:

- the author of the future retirement-review PR

Reviewed by:

- a human governance reviewer for the central steward path

## 1. Review Basics

| Field | Value |
|---|---|
| `review_id` | `<prototype-retirement-review-YYYYMMDD>` |
| `review_type` | `retirement` |
| `review_window` | `<YYYY-MM-DD to YYYY-MM-DD>` |
| `reviewer` | `<name or handle>` |
| `review_author` | `<name or handle>` |
| `related_prs` | `<PR links>` |
| `related_docs` | `docs/architecture/prototype_evidence_collection_plan_v1.md`, `docs/architecture/prototype_retirement_criteria_v1.md`, `docs/architecture/shadow_summary_disposition_v1.md`, `docs/architecture/central_steward_readonly_ingest_v1.md` |
| `current_runtime_posture` | `default-off / internal-only / not-canonical / no-actioning` |
| `retirement_scope_candidate` | `<runtime hook / docs archive / full prototype retirement>` |

## 2. Evidence Summary

Complete all fields using evidence gathered under the approved evidence collection plan.

| Evidence item | Observed value | Interpretation | Evidence source |
|---|---:|---|---|
| `shadow_summary_generation_frequency` | `<value>` | `<too low to justify / noisy / unclear>` | `<log or review note>` |
| `dedupe_hit_rate` | `<value>` | `<low-value / useful but not enough / unstable>` | `<log or review note>` |
| `cooldown_hit_rate` | `<value>` | `<low-value / useful but not enough / unstable>` | `<log or review note>` |
| `recovery_of_ratio` | `<value>` | `<little value / churn / unclear>` | `<log or review note>` |
| `false_positive_noise` | `<value>` | `<low / medium / high and why>` | `<log or review note>` |
| `decision_value` | `<value>` | `<low / none / insufficient>` | `<review note>` |
| `canonical_overlap` | `<value>` | `<low / medium / high and why>` | `<comparison note>` |

## 3. Boundary Checks

Every row must be completed with evidence, not opinion.

| Boundary check | Pass / Fail | Evidence | Notes |
|---|---|---|---|
| still `internal-only` at review time | `<pass/fail>` | `<evidence>` | `<note>` |
| still `not-canonical` | `<pass/fail>` | `<evidence>` | `<note>` |
| still does not affect `/status` | `<pass/fail>` | `<evidence>` | `<note>` |
| still does not affect `/daily` | `<pass/fail>` | `<evidence>` | `<note>` |
| still does not affect `/dashboard` truth | `<pass/fail>` | `<evidence>` | `<note>` |
| still does not write `data/state/*` | `<pass/fail>` | `<evidence>` | `<note>` |
| still does not touch bounded repair | `<pass/fail>` | `<evidence>` | `<note>` |
| still remains stoppable via feature flag or equivalent kill switch | `<pass/fail>` | `<evidence>` | `<note>` |

Retirement-pressure checks:

| Check | Pass / Fail | Evidence | Notes |
|---|---|---|---|
| observation value remains low | `<pass/fail>` | `<evidence>` | `<note>` |
| canonical overlap remains high | `<pass/fail>` | `<evidence>` | `<note>` |
| confusion pressure is rising | `<pass/fail>` | `<evidence>` | `<note>` |
| maintenance cost exceeds value | `<pass/fail>` | `<evidence>` | `<note>` |
| boundary erosion pressure appears | `<pass/fail>` | `<evidence>` | `<note>` |

## 4. Retirement Criteria Check

Map the evidence to the criteria in `docs/architecture/prototype_retirement_criteria_v1.md`.

| Retirement criterion | Pass / Fail | Evidence | Next action if failed |
|---|---|---|---|
| observation value remains low | `<pass/fail>` | `<evidence>` | `<keep current posture>` |
| producer contract diverges or is superseded | `<pass/fail>` | `<evidence>` | `<keep current posture>` |
| confusion risk starts rising | `<pass/fail>` | `<evidence>` | `<keep current posture or tighten docs>` |
| maintenance cost exceeds value | `<pass/fail>` | `<evidence>` | `<keep current posture>` |
| boundary erosion appears | `<pass/fail>` | `<evidence>` | `<keep current posture>` |

## 5. Decision

Select one:

- `keep`
- `retirement-review pass`
- `retirement-review fail`

Decision:

`<selected status>`

Decision rationale:

- `<reason 1>`
- `<reason 2>`
- `<reason 3>`

## 6. Next Action

If decision is `keep`:

- `<continue observation mode / no runtime change>`

If decision is `retirement-review pass`:

- `<open one dedicated minimal retirement PR for archive/removal>`

If decision is `retirement-review fail`:

- `<return to keep status or route to upgrade-observation only>`

## 7. Kill Switch / Rollback Note

Current kill switch:

- `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`

If retirement is approved:

- disable the prototype path before or alongside any removal PR
- keep rollback limited to restoring the prototype as `default-off / internal-only / not-canonical`
- do not reintroduce it as canonical state or formal alerting

## 8. Removal / Archive Note

Required only for retirement review.

| Field | Value |
|---|---|
| `archive_or_remove` | `<archive / remove>` |
| `proposed_scope` | `<files or docs>` |
| `historical_note_required` | `<yes/no>` |
| `out_of_scope` | `src/hongstr/**, scripts/refresh_state.sh, scripts/state_snapshots.py, data/state/*, canonical /status /daily /dashboard semantics` |
| `follow_on_docs` | `<docs to archive or keep as history>` |

Removal / archive rationale:

- `<why retirement is cleaner than indefinite keep>`

## 9. Out Of Scope Confirmation

Confirm all remain unchanged:

- `src/hongstr/**`
- `scripts/refresh_state.sh`
- `scripts/state_snapshots.py`
- `data/state/*`
- bounded repair / self-heal / dispatch retirement decisions
- canonical `/status` `/daily` `/dashboard` truth sources

## 10. Review Sign-Off

| Role | Name | Decision | Date |
|---|---|---|---|
| review author | `<name>` | `<decision>` | `<YYYY-MM-DD>` |
| governance reviewer | `<name>` | `<approve / request changes>` | `<YYYY-MM-DD>` |
