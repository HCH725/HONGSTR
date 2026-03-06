# HONGSTR Prototype Review Reviewer Checklist v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / checklist-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype review reviewer checklist PR
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

Use this checklist when reviewing any central steward shadow/prototype review PR.

This checklist is for reviewers only.

It complements, but does not replace:

- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- `docs/ops/prototype_review_kickoff_sop_v1.md`
- `docs/templates/prototype_evidence_summary_template_v1.md`
- `docs/templates/prototype_upgrade_review_template_v1.md`
- `docs/templates/prototype_retirement_review_template_v1.md`
- `docs/ops/prototype_review_package_index_v1.md`

This checklist is a review aid only.

It is not:

- rollout approval
- canonical status publication
- a reason to change `/status`, `/daily`, or `/dashboard`

If the review reaches a final outcome, record it with `docs/templates/prototype_review_decision_record_template_v1.md`.

## 0. Reviewer Role Split

Use the two checklists differently.

- `author checklist` verifies that the submitter assembled the package correctly before opening the PR
- `reviewer checklist` verifies that the submitted package is evidence-backed, boundary-safe, and ready for a governance decision

Reviewer rule:

- do not treat author completion as proof that the review should pass
- re-check the evidence, the boundaries, and the non-rollout scope yourself

## 1. How To Use

1. identify the review type first:
   - `upgrade-review`
   - `retirement-review`
2. stop immediately if the package is incomplete or mixed with rollout/runtime work
3. review evidence adequacy before discussing decision outcome
4. review boundary integrity before discussing decision outcome
5. record one of the allowed review outcomes only after the package passes completeness and boundary checks

If any required item fails:

- issue a `request-changes note`
- return for more evidence
- or stop the review and require the scope to be split

Use `docs/templates/prototype_review_request_changes_note_template_v1.md` when the reviewer needs a standardized return-for-fixes note.

## A. Review Package Completeness

- [ ] The PR clearly states the correct review type:
  - `upgrade-review`
  - or `retirement-review`
- [ ] The PR uses the correct review template for that type.
- [ ] An evidence summary is attached or linked.
- [ ] The author checklist is attached, linked, or clearly completed.
- [ ] The review package cites the governing docs:
  - `docs/architecture/prototype_evidence_collection_plan_v1.md`
  - `docs/architecture/prototype_retirement_criteria_v1.md`
  - `docs/ops/prototype_review_kickoff_sop_v1.md`
- [ ] The package is consistent with `docs/ops/prototype_review_package_naming_convention_v1.md`.
- [ ] The package remains review-only and does not mix in rollout or runtime changes.
- [ ] The package is complete enough to review without guessing missing context.

If any item above fails:

- the reviewer response should usually be a `request-changes note`, not substantive approval

## B. Evidence Adequacy

- [ ] The evidence window is complete.
- [ ] The minimum observation bar is met:
  - `14 calendar days`
  - `at least 5 manual observation sessions`
- [ ] If the review is an early retirement exception, the exception is explicitly justified and reviewer-sponsored.
- [ ] The evidence summary includes all required fields:
  - shadow summary generation frequency
  - dedupe hit rate
  - cooldown hit rate
  - `recovery_of_ratio`
  - `false_positive_noise`
  - `decision_value`
  - `canonical_overlap`
- [ ] Evidence sources are approved non-canonical sources only.
- [ ] There is no obvious evidence gap that prevents a reviewer from understanding value versus risk.
- [ ] The evidence distinguishes observed facts from interpretation.
- [ ] The evidence is strong enough to support a review decision, or else the PR explicitly asks for `insufficient evidence` with next action `continue observation`.

If evidence is thin or contradictory:

- request more evidence
- or require an extended observation window before continuing
- if a standardized note is needed, use request-changes reason `insufficient evidence` or `observation window incomplete` instead of ad hoc prose labels

## C. Boundary Checks

- [ ] The prototype is `internal-only`.
- [ ] The prototype is `not-canonical`.
- [ ] The review package does not affect `/status`.
- [ ] The review package does not affect `/daily`.
- [ ] The review package does not affect `/dashboard`.
- [ ] The review package does not write `data/state/*`.
- [ ] The review package does not create a second state writer.
- [ ] The review package does not touch bounded repair, self-heal, or arbitrary execution.
- [ ] The review package does not change `tg_cp` runtime.
- [ ] The review package still satisfies `review PR != rollout PR`.

Boundary response rule:

- if canonical boundaries are unclear, stop the review and return the PR
- if rollout scope is mixed in, require a split PR before continuing

## D. Decision Hygiene

- [ ] I have kept assessment status, decision outcome, and next action separate:
  - assessment status: `continue observation`, `candidate for upgrade-review`, `candidate for retirement-review`, `needs more evidence`
  - decision outcome: `keep`, `upgrade-review pass`, `upgrade-review fail`, `retirement-review pass`, `retirement-review fail`, `insufficient evidence`
  - next action: `continue observation`, `extend evidence window`, `open review PR`, `open retirement PR`, or `no action`
- [ ] I can map the submitted evidence to one of the allowed outcomes:
  - `keep`
  - `upgrade-review pass`
  - `upgrade-review fail`
  - `retirement-review pass`
  - `retirement-review fail`
  - `insufficient evidence`
- [ ] I do not need to rely on intuition alone to reach that conclusion.
- [ ] The chosen review type still matches the evidence.
- [ ] If the evidence points to the opposite review type, I have asked for redirect rather than forcing a pass/fail on the wrong template.
- [ ] If the evidence is incomplete, I have considered `insufficient evidence` or observation extension instead of over-deciding.
- [ ] Any approved next action remains a separate, smaller follow-on PR.
- [ ] I have confirmed again that `review PR != rollout PR`.

Reviewer escalation options:

- issue a `request-changes note`
- ask for longer observation
- redirect from `upgrade-review` to `retirement-review`
- redirect from `retirement-review` to `keep` with next action `continue observation`

## E. Kill Switch / Rollback / Stop Conditions

- [ ] If I see rollout drift, I will stop the review and require a separate PR.
- [ ] If I see canonical-boundary confusion, I will reject the package until the boundary is restated clearly.
- [ ] If I see a hidden runtime change, I will stop review and require the runtime change to be split out.
- [ ] If I see repeated pressure to make the prototype quasi-canonical, I will consider whether `retirement-review` is safer than continued ambiguity.
- [ ] I have confirmed the current kill switch remains `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`.
- [ ] I have confirmed no rollback would require writing or repairing canonical `data/state/*`.

## F. Reviewer Outcome

If the package is ready for a decision outcome, use one canonical label:

- `keep`
- `upgrade-review pass`
- `upgrade-review fail`
- `retirement-review pass`
- `retirement-review fail`
- `insufficient evidence`

If the reviewer is recording workflow posture instead of a final decision outcome, use a canonical reviewer response state:

- `request-changes note required`
- `return for fixes`
- `re-review allowed after fixes`
- `ready for decision record`

Reviewer response-state rule:

- use `request-changes note required` when this checklist is telling the reviewer to issue the standardized note
- use `ready for decision record` only after the package has cleared reviewer-side checks and may move to the decision record
- use `return for fixes` or `re-review allowed after fixes` only in the request-changes / resubmission flow, not as a final decision outcome
- treat `insufficient evidence for decision` as reviewer rationale plus request-changes reason or decision outcome wording, not as a response-state enum

Request-changes-reason rule:

- if the reviewer chooses `request-changes note required`, the blocking reasons should map to the canonical request-changes labels:
  - `insufficient evidence`
  - `incomplete template`
  - `boundary unclear`
  - `rollout mixed into review PR`
  - `canonical overlap unclear`
  - `observation window incomplete`

Required-fix label rule:

- if the reviewer chooses `request-changes note required`, the blocker-closure work should map to the canonical required-fix labels:
  - `missing evidence added`
  - `template completed`
  - `boundary wording clarified`
  - `rollout wording removed`
  - `canonical overlap explanation added`
  - `observation window extended`

Reviewer rationale:

- `<reason 1>`
- `<reason 2>`
- `<reason 3>`

Reviewer next action:

- `<next step>`

## G. Non-Rollout Reminder

State explicitly before final review sign-off:

- this reviewer checklist is a governance aid only
- this reviewer checklist is not rollout approval
- this reviewer checklist does not change canonical SSOT
- this reviewer checklist does not change `/status`, `/daily`, or `/dashboard`

## H. Reviewer Sign-Off

| Field | Value |
|---|---|
| `review_type` | `<upgrade-review / retirement-review>` |
| `reviewer` | `<name or handle>` |
| `date` | `<YYYY-MM-DD>` |
| `review_outcome_or_response_state` | `<selected outcome or reviewer response state>` |
| `package_complete` | `<yes / no>` |
| `boundary_clear` | `<yes / no>` |
| `rollout_mixed_in` | `<yes / no>` |
| `further_changes_required` | `<yes / no>` |
