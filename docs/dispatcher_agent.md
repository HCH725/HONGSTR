# Dispatcher Agent SOP

Status: archive-only / sandbox-only / deprecated as production governance
Canonical governance sources:

- `docs/architecture/agent_organization_governance_v1.md`
- `docs/architecture/escalation_taxonomy_v1.md`
- `docs/architecture/legacy_keep_kill_merge_review_v1.md`
- `docs/architecture/governance_dedupe_record_v1.md`

## 0. Why This Doc Was Downgraded

This document described a GitHub issue-comment `/dispatch` entrypoint that can trigger agent work outside Telegram.

That conflicts with the current governance target:

- Stage 7 keeps Telegram as the single outward operator entrance
- Stage 2 keeps top-level status deterministic and SSOT-first
- Stage 8 allows bounded report-only and repair workflows, but does not make GitHub issue comments a production operator ingress

## 1. Historical Scope Only

The paths below are historical dispatcher assets, not part of the target production governance model:

- `docs/dispatcher_agent.md`
- `docs/dispatcher_smoke.md`
- `scripts/dispatch/dispatch_issue.sh`
- `.github/workflows/dispatch.yml`
- `.github/ISSUE_TEMPLATE/task.yml`

Use them, if at all, for sandbox inspection only. Do not expand them, operationalize them further, or wire them into `tg_cp`.

## 2. Current Disposition

- production status: not canonical
- governance status: archive-only
- runtime status in this PR: unchanged
- next-step status: removal candidate after dependent docs/workflows are reviewed in a later smallest-unit PR

## 3. Removal Guidance

If a later PR retires the dispatcher path, it should:

1. remove or archive the issue-comment dispatch docs
2. retire the dispatcher workflow and issue template in the same smallest possible governance/runtime-safe slice
3. preserve evidence of the old flow in the dedupe record or release notes

## 4. Rollback

This file is docs-only. Rollback remains `git revert <commit_sha>`.
