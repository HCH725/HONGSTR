# HONGSTR Direct Dispatch Retirement v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / very-thin cleanup / no runtime wiring into core paths
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: direct `/dispatch` retirement
Plane: Governance docs plus legacy non-core cleanup
Expected SSOT/output impact: none

## 0. Scope

This PR retires only the direct `/dispatch` ingress chain:

- `.github/workflows/dispatch.yml`
- `scripts/dispatch/dispatch_issue.sh`
- `.github/ISSUE_TEMPLATE/task.yml`
- `docs/dispatcher_agent.md`
- `docs/dispatcher_smoke.md`
- dispatch-specific sections in `docs/governance/ccpm_adoption.md`

This PR does not process:

- `.github/workflows/self_heal.yml`
- `scripts/self_heal/**`
- `docs/self_heal.md`
- `tg_cp` runtime
- `src/hongstr/**`
- any SSOT producer/consumer path

## 1. Why Direct `/dispatch` Was Retired

The direct `/dispatch` chain conflicted with the current governance target in three ways:

### Stage 2

- it added an alternate operator-triggered path that could initiate repo mutation outside the normal SSOT-oriented governance chain
- even without creating a second state writer, it increased the chance of governance drift around who may initiate operational changes

### Stage 7

- it directly conflicted with the "central steward via Telegram as the single outward operator entrance" rule
- GitHub issue comments containing `/dispatch` became a second operator ingress

### Stage 8

- it was broader than the bounded, review-driven repair stance preserved for later self-heal review
- retiring `/dispatch` now keeps the diff small and avoids mixing direct dispatch retirement with the separate self-heal policy decision

## 2. Evidence

Pre-retirement evidence from the repo audit:

- `.github/workflows/dispatch.yml` listened on `issue_comment` and gated on comment text containing `/dispatch`
- `scripts/dispatch/dispatch_issue.sh` parsed `/dispatch`, opened branches/PRs, and referenced `docs/dispatcher_smoke.md`
- `.github/ISSUE_TEMPLATE/task.yml` explicitly described itself as a task unit dispatched via `/dispatch`
- `docs/dispatcher_agent.md` documented the GitHub issue-comment dispatcher flow
- `docs/governance/ccpm_adoption.md` still described `.github/workflows/dispatch.yml` and `.github/ISSUE_TEMPLATE/task.yml` as the historical dispatch workflow

These findings are also captured in:

- `docs/architecture/legacy_dispatcher_ingress_review_v1.md`

## 3. Retirement Action

Removed now:

- `.github/workflows/dispatch.yml`
- `scripts/dispatch/dispatch_issue.sh`
- `.github/ISSUE_TEMPLATE/task.yml`
- `docs/dispatcher_agent.md`
- `docs/dispatcher_smoke.md`

Updated in place:

- `docs/governance/ccpm_adoption.md`
- canonical governance records that previously marked `/dispatch` as a removal candidate

## 4. Why This Is Safe

This retirement is intentionally narrow:

- it removes only the direct `/dispatch` chain already classified as conflicting with Stage 7
- it does not modify `src/hongstr/**`
- it does not modify `_local/telegram_cp/tg_cp_server.py`
- it does not modify `scripts/state_snapshots.py` or `scripts/refresh_state.sh`
- it does not touch `.github/workflows/self_heal.yml` or `scripts/self_heal/**`
- it does not change any SSOT output, deterministic fallback, or top-level status consumer

## 5. Why Self-Heal Is Out Of Scope

`/selfheal` is also a non-Telegram ingress, but it is materially more bounded than `/dispatch`:

- it is tied to allowlisted repair tickets
- it runs required checks
- it opens draft PRs rather than broad task dispatch

That chain still needs a separate architecture decision. Mixing it into this retirement PR would blur the governance line between "direct alternate ingress" and "bounded repair exception".

## 6. Removal Plan

This PR completes the direct `/dispatch` retirement as one smallest unit:

1. remove the direct dispatch workflow, executor, and dispatch-specific issue template
2. remove the direct dispatch-only docs/artifacts that become orphaned after step 1
3. preserve the history in retirement/audit docs rather than in live operator docs
4. leave self-heal and all runtime SSOT / Telegram paths unchanged

## 7. Degrade

Degrade stance:

- keep retirement docs as the historical record
- if any stakeholder still needs the old chain for forensic reference, the governance docs retain the audit trail without re-enabling the ingress

## 8. Kill Switch

- close this stacked PR, or
- revert the retirement commit with `git revert <commit_sha>`

Because the retired chain is outside `src/hongstr/**`, outside `tg_cp` runtime, and outside the state writer boundary, rollback remains localized to legacy governance assets.
