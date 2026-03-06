# HONGSTR Prototype Review Package Naming Convention v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / naming-convention-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype review package naming convention PR
Plane: central steward prototype review package naming governance
Expected SSOT/output impact: none

## 0. Purpose

This file standardizes how future central steward shadow/prototype review packages should be named.

It covers:

- review PR titles
- review type labels
- package section order
- evidence attachment names
- template / checklist / SOP citation style

It does not:

- authorize rollout
- authorize formal Telegram alerting
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`

Core rule:

- naming convention improves governance consistency only
- naming convention does not grant rollout approval
- `review package != rollout PR`

## 1. Scope

This naming convention applies to:

- future `upgrade review` PRs
- future `retirement review` PRs
- future `evidence review` PRs, if such a docs-only review is opened
- reusable `package example` docs
- package-local evidence summaries and supporting attachments

This naming convention does not apply to:

- runtime artifact names under `data/state/*`
- runtime artifact names under `_local/**`
- Telegram message text
- `src/hongstr/**`

## 2. Canonical Naming Elements

Use these canonical naming elements.

### 2.1 Review type labels

| Human label | Required slug | Use case |
|---|---|---|
| `upgrade review` | `upgrade-review` | asks whether the prototype is ready for a later, separate, non-canonical operator-visible review path |
| `retirement review` | `retirement-review` | asks whether the prototype should be archived or removed |
| `evidence review` | `evidence-review` | docs-only review of evidence sufficiency before upgrade or retirement is considered |
| `package example` | `package-example` | reusable example package, not a live decision artifact |

### 2.2 Prototype identifier

Current default prototype identifier:

- human label: `central steward shadow/prototype`
- required slug: `central-steward-shadow-prototype`

Rule:

- use the slug in filenames and PR titles
- use the human label only in explanatory prose

### 2.3 Review window formats

Use these two formats consistently:

- display format: `YYYY-MM-DD..YYYY-MM-DD`
- filename format: `YYYYMMDD_YYYYMMDD`

Examples:

- display: `2026-03-01..2026-03-14`
- filename: `20260301_20260314`

## 3. Required Versus Optional Naming Elements

| Element | Required for review PR title | Required for attachment filename | Required for example doc | Notes |
|---|---|---|---|---|
| `review_type` | yes | yes | yes | use canonical slug |
| `prototype_id` | yes | yes | yes | use `central-steward-shadow-prototype` until another prototype exists |
| `review_window` | yes for live reviews | yes for live review attachments | optional for reusable examples | required for `upgrade-review`, `retirement-review`, and `evidence-review` |
| `artifact_kind` | no | yes | no | examples: `evidence-summary`, `review`, `author-checklist` |
| `date` | optional if already implicit in review window | optional if review window already included | optional | do not duplicate if it adds no clarity |
| `version` | no for live review PR titles | optional for attachments | yes for reusable repo docs | reusable repo docs stay on `_v1` naming |

Rule of thumb:

- live review packages should prefer `review_type + prototype_id + review_window`
- reusable docs should prefer stable `_v1` names

## 4. Review PR Title Format

Recommended future review PR title format:

```text
[codex] prototype {review_type_slug}: {prototype_id} [{review_window_display}]
```

Examples:

- `[codex] prototype upgrade-review: central-steward-shadow-prototype [2026-03-01..2026-03-14]`
- `[codex] prototype retirement-review: central-steward-shadow-prototype [2026-03-01..2026-03-14]`
- `[codex] prototype evidence-review: central-steward-shadow-prototype [2026-03-01..2026-03-14]`

Rules:

- always use the canonical review type slug
- always include the prototype slug
- always include the review window for live review PRs
- do not put rollout language in the title

Forbidden title patterns:

- anything that implies rollout
- anything that implies canonical status change
- vague titles such as `prototype updates` or `steward cleanup`

## 5. Package Section Order

Future review packages should keep this section order whenever possible:

1. `Review Basics`
2. `Evidence Summary`
3. `Boundary Checks`
4. `Criteria Check`
5. `Decision`
6. `Next Action`
7. `Kill Switch / Rollback Note`
8. `Out Of Scope Confirmation`
9. `Review Sign-Off`

For `package example` docs, the section order may add:

- `Purpose`
- `How To Use`
- `Minimal Flow`

But the embedded review example should still preserve the standard review order.

## 6. Evidence Attachment Naming

If the review package uses separate Markdown attachments or linked docs, use this filename pattern:

```text
prototype-{prototype_id}-{review_type_slug}-{review_window_filename}-{artifact_kind}.md
```

Recommended artifact kinds:

- `evidence-summary`
- `review`
- `author-checklist`
- `kickoff-note`
- `boundary-note`

Examples:

- `prototype-central-steward-shadow-prototype-upgrade-review-20260301_20260314-evidence-summary.md`
- `prototype-central-steward-shadow-prototype-upgrade-review-20260301_20260314-review.md`
- `prototype-central-steward-shadow-prototype-retirement-review-20260301_20260314-author-checklist.md`

If the package is embedded directly in the PR body instead of separate files:

- keep the same names as section labels
- keep the same `review_type`, `prototype_id`, and `review_window` values in the `Review Basics` block

## 7. Template / Checklist / SOP Citation Style

Use repo-path citations exactly as paths, not prose nicknames.

Required references for a live review package:

- `docs/architecture/prototype_evidence_collection_plan_v1.md`
- `docs/architecture/prototype_retirement_criteria_v1.md`
- `docs/ops/prototype_review_kickoff_sop_v1.md`
- `docs/templates/prototype_review_pr_author_checklist_v1.md`
- one matching template:
  - `docs/templates/prototype_upgrade_review_template_v1.md`
  - or `docs/templates/prototype_retirement_review_template_v1.md`

Optional but recommended references:

- `docs/examples/prototype_review_package_example_v1.md`
- `docs/architecture/shadow_summary_disposition_v1.md`
- `docs/architecture/central_steward_readonly_ingest_v1.md`

Citation rule:

- paths must appear verbatim so a reviewer can jump directly to the governing document

## 8. Review Type Naming Guidance

### 8.1 Upgrade review

Use when:

- the package is asking whether the prototype may advance toward a later, separate, explicitly non-canonical operator-visible path

Must include:

- `upgrade-review`
- `review_window`
- evidence summary showing usefulness and bounded confusion risk

### 8.2 Retirement review

Use when:

- the package is asking whether the prototype should be archived or removed

Must include:

- `retirement-review`
- `review_window`
- evidence summary showing low value, high overlap, high noise, or boundary erosion

### 8.3 Evidence review

Use when:

- the package is only assessing whether the evidence is sufficient to justify a later upgrade or retirement review

Must include:

- `evidence-review`
- `review_window`
- a clear statement that this is not yet an upgrade or retirement decision

### 8.4 Package example

Use when:

- the document is only a reusable example or training artifact

Must include:

- `package-example`
- stable repo-doc versioning such as `_v1`

Should not include:

- a live review window unless the example is intentionally illustrating one

## 9. Naming Examples

Example 1: live upgrade review PR title

```text
[codex] prototype upgrade-review: central-steward-shadow-prototype [2026-03-01..2026-03-14]
```

Example 2: live retirement review evidence attachment

```text
prototype-central-steward-shadow-prototype-retirement-review-20260301_20260314-evidence-summary.md
```

Example 3: reusable example doc title line

```text
HONGSTR Prototype Review Package Example v1
```

Example 4: live evidence review attachment

```text
prototype-central-steward-shadow-prototype-evidence-review-20260301_20260314-review.md
```

## 10. Governance Reminder

Interpret this convention correctly:

- it is for naming consistency only
- it does not approve rollout
- it does not approve formal alerting
- it does not change canonical SSOT
- it does not change `/status`, `/daily`, or `/dashboard`

If a proposed package uses a compliant name but violates governance boundaries:

- reject the package anyway

## 11. Canonical Answer

The canonical naming answer in v1 is:

- standardize on `review_type + prototype_id + review_window`
- keep section order stable across review packages
- name attachments by `prototype-{prototype_id}-{review_type}-{review_window}-{artifact_kind}.md`
- use exact repo paths when citing evidence plan, criteria, templates, checklist, and SOP
- keep naming governance-only and never treat it as rollout approval
