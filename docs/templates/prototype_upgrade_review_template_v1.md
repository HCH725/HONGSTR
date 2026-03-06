# HONGSTR Prototype Upgrade Review Template v1

Use this template only for a future `upgrade review` of the central steward shadow/prototype path.

Before opening a review PR, satisfy `docs/ops/prototype_review_kickoff_sop_v1.md`.
Authors should also complete `docs/templates/prototype_review_pr_author_checklist_v1.md` before opening the PR.
Authors may use `docs/examples/prototype_review_package_example_v1.md` as a package assembly example.
Authors should follow `docs/ops/prototype_review_package_naming_convention_v1.md` for review package titles and attachment names.
Authors should use `docs/templates/prototype_evidence_summary_template_v1.md` for the evidence summary block.
Reviewers should record the final outcome in `docs/templates/prototype_review_decision_record_template_v1.md`.

Do not use this template for rollout.

Do not use this template for retirement review. Use `docs/templates/prototype_retirement_review_template_v1.md` instead.

## 0. Review Start Rule

Start this template only when:

- the observation window defined in `docs/architecture/prototype_evidence_collection_plan_v1.md` has completed
- evidence has been summarized in a human-reviewed note or PR
- the review author believes the path may be ready for `upgrade review`

Filled by:

- the author of the future upgrade-review PR

Reviewed by:

- a human governance reviewer for the central steward path

## 1. Review Basics

| Field | Value |
|---|---|
| `review_id` | `<prototype-upgrade-review-YYYYMMDD>` |
| `review_type` | `upgrade` |
| `review_window` | `<YYYY-MM-DD to YYYY-MM-DD>` |
| `reviewer` | `<name or handle>` |
| `review_author` | `<name or handle>` |
| `related_prs` | `<PR links>` |
| `related_docs` | `docs/architecture/prototype_evidence_collection_plan_v1.md`, `docs/architecture/prototype_retirement_criteria_v1.md`, `docs/architecture/shadow_summary_disposition_v1.md`, `docs/architecture/central_steward_readonly_ingest_v1.md` |
| `current_runtime_posture` | `default-off / internal-only / not-canonical / no-actioning` |
| `proposed_next_step` | `<usually operator-visible but explicitly non-canonical shadow summary, or keep current posture>` |

## 2. Evidence Summary

Complete all fields using evidence gathered under the approved evidence collection plan.

| Evidence item | Observed value | Interpretation | Evidence source |
|---|---:|---|---|
| `shadow_summary_generation_frequency` | `<value>` | `<low / medium / high and why>` | `<log or review note>` |
| `dedupe_hit_rate` | `<value>` | `<useful / low-value / unstable>` | `<log or review note>` |
| `cooldown_hit_rate` | `<value>` | `<useful / low-value / unstable>` | `<log or review note>` |
| `recovery_of_ratio` | `<value>` | `<useful closure / churn / unclear>` | `<log or review note>` |
| `false_positive_noise` | `<value>` | `<low / medium / high and why>` | `<log or review note>` |
| `decision_value` | `<value>` | `<net-new context or not>` | `<review note>` |
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

Upgrade-specific message check:

| Check | Pass / Fail | Evidence | Notes |
|---|---|---|---|
| proposed visible wording is explicitly `NOT CANONICAL` | `<pass/fail>` | `<draft wording>` | `<note>` |
| proposed visible wording is explicitly `NOT A FORMAL ALERT` | `<pass/fail>` | `<draft wording>` | `<note>` |
| proposed visible wording is explicitly `NO ACTION REQUIRED UNLESS CONFIRMED BY /status OR /daily` | `<pass/fail>` | `<draft wording>` | `<note>` |
| Telegram single-entry semantics remain intact | `<pass/fail>` | `<reasoning>` | `<note>` |

## 4. Upgrade Criteria Check

Map the evidence to the criteria in `docs/architecture/prototype_retirement_criteria_v1.md`.

| Upgrade criterion | Pass / Fail | Evidence | Next action if failed |
|---|---|---|---|
| producer contract stability | `<pass/fail>` | `<evidence>` | `<stay internal-log only / collect more evidence>` |
| message distinction is testable | `<pass/fail>` | `<evidence>` | `<rewrite proposal or stop>` |
| operational usefulness is evidenced | `<pass/fail>` | `<evidence>` | `<stay internal-log only>` |
| confusion risk is bounded | `<pass/fail>` | `<evidence>` | `<stop upgrade review>` |
| no P0 dependency emerges | `<pass/fail>` | `<evidence>` | `<stop upgrade review>` |
| single-entry semantics survive | `<pass/fail>` | `<evidence>` | `<stop upgrade review>` |

## 5. Decision

Select one:

- `keep`
- `upgrade-review pass`
- `upgrade-review fail`

Decision:

`<selected status>`

Decision rationale:

- `<reason 1>`
- `<reason 2>`
- `<reason 3>`

## 6. Next Action

If decision is `keep`:

- `<continue observation window / collect more evidence / no runtime change>`

If decision is `upgrade-review pass`:

- `<open one dedicated minimal runtime PR for operator-visible but explicitly non-canonical shadow summary>`

If decision is `upgrade-review fail`:

- `<remain internal-log only or redirect to retirement review>`

## 7. Kill Switch / Rollback Note

Current kill switch:

- `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`

If a later upgrade PR is opened, rollback must still be:

- revert to `default-off`
- revert any operator-visible shadow summary separately from canonical alerting
- keep `/status`, `/daily`, and `/dashboard` on canonical SSOT only

## 8. Out Of Scope Confirmation

Confirm all remain unchanged:

- `src/hongstr/**`
- `scripts/refresh_state.sh`
- `scripts/state_snapshots.py`
- `data/state/*`
- bounded repair / self-heal / dispatch retirement decisions
- canonical `/status` `/daily` `/dashboard` truth sources

## 9. Review Sign-Off

| Role | Name | Decision | Date |
|---|---|---|---|
| review author | `<name>` | `<decision>` | `<YYYY-MM-DD>` |
| governance reviewer | `<name>` | `<approve / request changes>` | `<YYYY-MM-DD>` |
