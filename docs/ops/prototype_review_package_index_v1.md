# HONGSTR Prototype Review Package Index v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / index-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype review package index PR
Plane: central steward prototype review/package governance
Expected SSOT/output impact: none

## 0. Purpose

This file is the single-entry landing doc for the central steward shadow/prototype review chain.

Use it when a future author needs to answer:

- where to start
- which document to read next
- which file is criteria versus evidence versus template versus SOP
- how to assemble a review package without drifting into rollout

This index is governance-only.

It does not:

- authorize rollout
- authorize formal Telegram alerting
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- change `tg_cp` runtime

Core rule:

- `review/package docs != rollout PR`

## 1. Scope

This index applies only to the current central steward shadow/prototype path:

- default-off
- internal-only
- not-canonical
- no-actioning

It covers only the review/package governance chain around that prototype.

It does not cover:

- `src/hongstr/**`
- `scripts/refresh_state.sh`
- `scripts/state_snapshots.py`
- `data/state/*`
- bounded repair
- self-heal or retired direct `/dispatch` paths

## 2. Current Boundary Reminder

Before using any document below, keep these boundaries fixed:

- the prototype is not canonical state
- the prototype is not a second writer
- the prototype must not back-fill `/status`, `/daily`, or `/dashboard`
- the prototype must remain read-only against `reports/state_atomic/alerts_*`
- review/package documents must not be used as rollout approval

## 3. File Map

### 3.1 Context And Boundary Docs

Use these first to understand what the prototype is and what it is not.

- `docs/architecture/central_steward_readonly_ingest_v1.md`
- `docs/architecture/shadow_summary_disposition_v1.md`
- `docs/architecture/atomic_alert_producer_invocation_decision_v1.md`

### 3.2 Criteria Docs

Use these to decide what counts as `keep`, `upgrade`, or `retire`.

- `docs/architecture/prototype_retirement_criteria_v1.md`

### 3.3 Evidence Plan

Use this to know what evidence must be collected before any live review can start.

- `docs/architecture/prototype_evidence_collection_plan_v1.md`

### 3.4 SOP

Use this to decide whether a review PR may start at all.

- `docs/ops/prototype_review_kickoff_sop_v1.md`

### 3.5 Naming Convention

Use this to keep review package naming, title format, and attachment naming consistent.

- `docs/ops/prototype_review_package_naming_convention_v1.md`

### 3.6 Templates

Use these to structure the review package itself.

- `docs/templates/prototype_evidence_summary_template_v1.md`
- `docs/templates/prototype_upgrade_review_template_v1.md`
- `docs/templates/prototype_retirement_review_template_v1.md`

### 3.7 Checklist

Use these at the correct stage of the review flow.

- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- `docs/templates/prototype_review_reviewer_checklist_v1.md`

### 3.8 Example Package

Use this when an author wants a concrete package assembly example.

- `docs/examples/prototype_review_package_example_v1.md`
- `docs/examples/prototype_resubmission_example_v1.md`

## 4. Recommended Reading Order

Read in this order.

1. `docs/architecture/central_steward_readonly_ingest_v1.md`
2. `docs/architecture/shadow_summary_disposition_v1.md`
3. `docs/architecture/atomic_alert_producer_invocation_decision_v1.md`
4. `docs/architecture/prototype_retirement_criteria_v1.md`
5. `docs/architecture/prototype_evidence_collection_plan_v1.md`
6. `docs/ops/prototype_review_kickoff_sop_v1.md`
7. `docs/ops/prototype_review_package_naming_convention_v1.md`
8. `docs/templates/prototype_evidence_summary_template_v1.md`
9. `docs/templates/prototype_upgrade_review_template_v1.md`
10. `docs/templates/prototype_retirement_review_template_v1.md`
11. `docs/templates/prototype_review_pr_author_checklist_v1.md`
12. `docs/examples/prototype_review_package_example_v1.md`

Reason for this order:

- context first
- criteria second
- evidence plan third
- kickoff gate fourth
- package assembly docs last

## 5. Minimal Review-Package Flow

When a future author actually wants to open a review PR, use this minimum flow.

1. read the boundary/context docs and confirm the prototype is still `default-off`, `internal-only`, and `not-canonical`
2. read `docs/architecture/prototype_retirement_criteria_v1.md`
3. complete the evidence window defined in `docs/architecture/prototype_evidence_collection_plan_v1.md`
4. fill `docs/templates/prototype_evidence_summary_template_v1.md`
5. choose exactly one review type:
   - `upgrade review`
   - `retirement review`
6. fill the matching review template
7. complete `docs/templates/prototype_review_pr_author_checklist_v1.md`
8. use `docs/ops/prototype_review_kickoff_sop_v1.md` as the final gate
9. after the PR opens, reviewers use `docs/templates/prototype_review_reviewer_checklist_v1.md`
10. if the package gets `request changes`, authors complete `docs/templates/prototype_re_review_resubmission_checklist_v1.md` before resubmitting
11. use `docs/ops/prototype_review_package_naming_convention_v1.md` to format the PR title and attachments
12. use `docs/examples/prototype_review_package_example_v1.md` if the initial package still feels unclear
13. use `docs/examples/prototype_resubmission_example_v1.md` if the re-review flow still feels unclear

If any prerequisite fails:

- stop
- keep the prototype in observation mode
- do not open the review PR yet

## 6. Which Document To Use For What

| Need | Governing file |
|---|---|
| understand read-only ingest boundary | `docs/architecture/central_steward_readonly_ingest_v1.md` |
| understand current shadow-summary posture | `docs/architecture/shadow_summary_disposition_v1.md` |
| understand producer invocation posture | `docs/architecture/atomic_alert_producer_invocation_decision_v1.md` |
| decide keep / upgrade / retire criteria | `docs/architecture/prototype_retirement_criteria_v1.md` |
| know which evidence to collect | `docs/architecture/prototype_evidence_collection_plan_v1.md` |
| know whether review may start | `docs/ops/prototype_review_kickoff_sop_v1.md` |
| standardize package naming | `docs/ops/prototype_review_package_naming_convention_v1.md` |
| write evidence summary | `docs/templates/prototype_evidence_summary_template_v1.md` |
| write upgrade review | `docs/templates/prototype_upgrade_review_template_v1.md` |
| write retirement review | `docs/templates/prototype_retirement_review_template_v1.md` |
| pre-submit self-check | `docs/templates/prototype_review_pr_author_checklist_v1.md` |
| post-request-changes resubmission self-check | `docs/templates/prototype_re_review_resubmission_checklist_v1.md` |
| reviewer-side review gate | `docs/templates/prototype_review_reviewer_checklist_v1.md` |
| see one assembled example | `docs/examples/prototype_review_package_example_v1.md` |
| see one resubmission flow example | `docs/examples/prototype_resubmission_example_v1.md` |

## 7. Non-Rollout Reminder

Interpret this entire governance chain correctly:

- these files support review/package preparation only
- these files do not approve runtime rollout
- these files do not approve operator-visible Telegram summary
- these files do not change canonical SSOT
- these files do not change `/status`, `/daily`, or `/dashboard`

Any later rollout discussion, if ever approved, must be:

- separate
- smaller
- evidence-backed
- reviewed after the governance chain is complete

## 8. Canonical Answer

The canonical v1 answer is:

- start from this index
- read context and boundary docs first
- use criteria and evidence plan before touching templates
- use SOP and checklist as the final gate before any review PR
- treat every package doc as governance-only, not rollout authorization
