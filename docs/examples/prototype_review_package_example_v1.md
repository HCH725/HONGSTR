# HONGSTR Prototype Review Package Example v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / example-package-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype review package example PR
Plane: central steward prototype review package example
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

This file shows a future author how to assemble a minimal review package for the central steward shadow/prototype path.

This package is an example only.

It does not:

- approve rollout
- approve formal Telegram alerting
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`

Core rule:

- `review PR != rollout PR`

## 1. When To Use This Example Package

Use this example package only when:

- the evidence window has completed
- the author is preparing either:
  - `upgrade-review`
  - or `retirement-review`
- the author wants one place that shows how evidence, template, checklist, and SOP fit together

Do not use this example package as:

- a rollout request
- a runtime change request
- a substitute for the evidence plan or lifecycle criteria

If you need the full document map first, start with `docs/ops/prototype_review_package_index_v1.md`.
If any field label or enum meaning is unclear, use `docs/ops/prototype_review_field_glossary_v1.md`.
If you need the post-`request-changes note` flow specifically, use `docs/examples/prototype_resubmission_example_v1.md`.

For title, attachment, and section-order conventions, see `docs/ops/prototype_review_package_naming_convention_v1.md`.

## 2. Package Manifest

A complete review package should contain these pieces:

| Package item | Purpose | Required source |
|---|---|---|
| evidence summary | proves the review is evidence-based | `docs/templates/prototype_evidence_summary_template_v1.md` |
| review template | structures the formal review | `docs/templates/prototype_upgrade_review_template_v1.md` or `docs/templates/prototype_retirement_review_template_v1.md` |
| author checklist | confirms the author did not skip prerequisites | `docs/templates/prototype_review_pr_author_checklist_v1.md` |
| re-review resubmission checklist | confirms request-changes items carry canonical blocker-closure status, blocker-evidence-reference labels, blocker target-hint wording, blocker multiplicity hints, blocker ordering hints, blocker applicability hints, canonical blocker placeholder shapes, canonical blocker field captions, canonical blocker rendering rules, and canonical blocker live-field cue phrases before resubmission | `docs/templates/prototype_re_review_resubmission_checklist_v1.md` |
| decision record | standardizes the reviewer’s final outcome once review is complete | `docs/templates/prototype_review_decision_record_template_v1.md` |
| request-changes note | standardizes canonical `request_changes_reason` labels, required-fix labels, plus reviewer response-state and return-for-fixes feedback when the package is not ready | `docs/templates/prototype_review_request_changes_note_template_v1.md` |
| kickoff SOP reference | defines whether the review may start at all | `docs/ops/prototype_review_kickoff_sop_v1.md` |
| lifecycle criteria reference | defines what counts as keep / upgrade / retire | `docs/architecture/prototype_retirement_criteria_v1.md` |
| boundary references | restate non-canonical / read-only limits | `docs/architecture/shadow_summary_disposition_v1.md` and `docs/architecture/central_steward_readonly_ingest_v1.md` |

## 3. Minimal Flow

Use this flow in order.

1. confirm the evidence window is complete
2. choose `upgrade-review` or `retirement-review`
3. fill the matching review template
4. complete the author checklist
5. use the kickoff SOP to decide whether the review PR may be opened

If any step fails:

- stop
- keep the prototype in observation mode
- do not open the review PR yet

## 4. Example Package Assembly

This is the smallest acceptable review package layout.

### 4.1 Step 1: Confirm evidence window

Author confirms:

- `14 calendar days` completed
- `at least 5 manual observation sessions` completed
- evidence summary exists

If not true:

- assessment status = `needs more evidence`
- next action = `continue observation`
- do not open review PR yet

### 4.2 Step 2: Select review type

Choose exactly one:

- `upgrade-review`
- `retirement-review`

If `upgrade-review`:

- use `docs/templates/prototype_upgrade_review_template_v1.md`

If `retirement-review`:

- use `docs/templates/prototype_retirement_review_template_v1.md`

### 4.3 Step 3: Fill the review template

At minimum, complete:

- Evidence summary using `docs/templates/prototype_evidence_summary_template_v1.md`
- Review basic information
- Evidence summary
- Boundary checks
- Decision
- Next action
- Kill switch / rollback note

### 4.4 Step 4: Complete the author checklist

Author must confirm:

- evidence window complete
- correct review type selected
- correct template selected
- evidence summary attached
- `internal-only`
- `not-canonical`
- does not affect `/status`
- does not affect `/daily`
- does not affect `/dashboard`
- does not write `data/state/*`
- does not change `tg_cp` runtime
- does not touch bounded repair
- `review PR != rollout PR`

### 4.5 Step 5: Run kickoff SOP gate

Before opening the PR, the author uses:

- `docs/ops/prototype_review_kickoff_sop_v1.md`

The PR may open only if:

- kickoff prerequisites are satisfied
- required materials are attached
- no forbidden mixed scope appears

## 5. Minimal Example Structure

The following is a minimal example structure an author can copy.

```md
# Prototype Review Package

## Review Basics
- review_id: <prototype-upgrade-review-YYYYMMDD or prototype-retirement-review-YYYYMMDD>
- review_type: <upgrade-review or retirement-review>
- review_window: <YYYY-MM-DD..YYYY-MM-DD>
- author: <name or handle>
- reviewer: <name or handle>
- related_docs:
  - docs/templates/prototype_evidence_summary_template_v1.md
  - docs/architecture/prototype_evidence_collection_plan_v1.md
  - docs/architecture/prototype_retirement_criteria_v1.md
  - docs/ops/prototype_review_kickoff_sop_v1.md

## Evidence Summary
- shadow summary generation frequency: <value>
- dedupe hit rate: <value>
- cooldown hit rate: <value>
- recovery_of_ratio: <value>
- false_positive_noise: <value>
- decision_value: <value>
- canonical_overlap: <value>

## Boundary Checks
- internal-only: <pass/fail>
- not-canonical: <pass/fail>
- does not affect `/status`: <pass/fail>
- does not affect `/daily`: <pass/fail>
- does not affect `/dashboard`: <pass/fail>
- does not write `data/state/*`: <pass/fail>
- does not change `tg_cp` runtime: <pass/fail>
- does not touch bounded repair: <pass/fail>
- review PR != rollout PR: <pass/fail>

## Decision
- requested decision: <keep / upgrade-review pass / upgrade-review fail / retirement-review pass / retirement-review fail / insufficient evidence>
- rationale: <short explanation>

## Next Action
- selected next action: <continue observation / extend evidence window / open review PR / open retirement PR / no action>

## Kill Switch / Rollback Note
- HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0
- no canonical rollback needed
```

## 6. Example Package Notes

Interpret this package correctly:

- it is a packaging example, not an approval
- it is a document assembly example, not a runtime plan
- it is a review starter, not a rollout decision

Boundary reminder:

- no example package may change `src/hongstr/**`
- no example package may change `scripts/refresh_state.sh`
- no example package may change `scripts/state_snapshots.py`
- no example package may change `data/state/*`
- no example package may change `tg_cp` runtime
- no example package may change `/status`, `/daily`, or `/dashboard` truth behavior

## 7. Recommended Author Workflow

Recommended order for future authors:

1. fill the evidence summary first
2. choose the review type second
3. fill the matching review template third
4. complete the author checklist fourth
5. use the kickoff SOP as the final gate before opening the PR

This order avoids the most common failure mode:

- opening a review PR before evidence, template, and boundary checks are actually ready

## 8. Canonical Answer

The canonical example-package answer in v1 is:

- package the review around evidence summary, matching template, author checklist, and kickoff SOP
- keep the package governance-only
- keep `review PR != rollout PR` explicit
- keep all package contents non-canonical and non-runtime-changing
