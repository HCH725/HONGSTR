# HONGSTR Prototype Enum Alignment Record v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / alignment-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype enum alignment PR
Plane: central steward prototype review/package governance
Expected SSOT/output impact: none

## 0. Purpose

This record captures the enum, label, and spelling drift found across the prototype review/package docs and the canonical labels that now govern v1.

This file is governance alignment only.

It does not:

- approve rollout
- approve formal Telegram alerting
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- change `tg_cp` runtime

## 1. Scope

This alignment applies to:

- `docs/ops/prototype_review_field_glossary_v1.md`
- `docs/templates/prototype_evidence_summary_template_v1.md`
- `docs/templates/prototype_upgrade_review_template_v1.md`
- `docs/templates/prototype_retirement_review_template_v1.md`
- `docs/templates/prototype_review_decision_record_template_v1.md`
- `docs/templates/prototype_review_request_changes_note_template_v1.md`
- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- `docs/templates/prototype_review_reviewer_checklist_v1.md`
- `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- `docs/examples/prototype_review_package_example_v1.md`
- `docs/examples/prototype_resubmission_example_v1.md`
- `docs/ops/prototype_review_package_index_v1.md`

## 2. Drift To Canonical Mapping

| Drift found | Canonical label in v1 | Notes |
|---|---|---|
| `upgrade` | `upgrade-review` | Use for `review_type` values and review package labels. |
| `retirement` | `retirement-review` | Use for `review_type` values and review package labels. |
| `evidence review` | `evidence-review` | Use only where the evidence-summary template explicitly allows it. |
| `internal_only` | `internal-only` | Boundary posture label only. |
| `not_canonical` | `not-canonical` | Boundary posture label only. |
| `no_actioning` | `no-actioning` | Boundary posture label only. |
| `review_author` | `author` | `author` is the canonical field label. |
| `false positive / noise` as a field label | `false_positive_noise` | Free-form prose may still explain the field, but the field label should stay canonical. |
| combined `insufficient evidence / continue observation` | decision outcome `insufficient evidence` plus next action `continue observation` | Do not merge decision outcome and next action into one label. |
| `request changes` used as the artifact name | `request-changes note` | Keep `request changes` only as generic prose for the GitHub review action when needed. |
| `request changes before review` | `request-changes note required` | This is a reviewer response state, not a final decision outcome. |
| `YYYY-MM-DD to YYYY-MM-DD` | `YYYY-MM-DD..YYYY-MM-DD` | Canonical `review_window` format. |

## 3. Deprecated Aliases

The following aliases may still appear in older PRs or historical examples, but they are no longer recommended for new review packages:

- `upgrade`
- `retirement`
- `internal_only`
- `not_canonical`
- `no_actioning`
- `review_author`
- combined `insufficient evidence / continue observation`
- `request changes before review`

## 4. Canonical Labels Authors Should Use

Use these labels going forward:

- `review_type`
  - `upgrade-review`
  - `retirement-review`
  - `evidence-review` only where explicitly allowed
- boundary posture
  - `internal-only`
  - `not-canonical`
  - `no-actioning`
- recurring field labels
  - `author`
  - `false_positive_noise`
  - `decision_value`
  - `canonical_overlap`
  - `request_changes_reason`
- decision outcome
  - `keep`
  - `upgrade-review pass`
  - `upgrade-review fail`
  - `retirement-review pass`
  - `retirement-review fail`
  - `insufficient evidence`
- next action
  - `continue observation`
  - `open upgrade review`
  - `open retirement review`
  - `open rollout candidate PR`
  - `extend evidence window`
  - `no action`

## 5. Files Aligned In This PR

This PR aligns the listed files by naming normalization only:

- glossary
- templates
- examples
- package index

No runtime files, no canonical state writers, and no `data/state/*` paths are changed.

## 6. Non-Rollout Reminder

Interpret this record correctly:

- it standardizes doc labels only
- it does not authorize rollout
- it does not authorize operator-visible Telegram summary
- it does not change canonical SSOT
- it does not change `/status`, `/daily`, or `/dashboard`
