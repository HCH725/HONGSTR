# Linear-First Control Package

## Purpose

This package closes the owner-card acceptance gap for `HONG-43`.

It defines the repo-backed governance baseline for:

- initiate
- register in Linear
- execute
- track
- close

It does not implement automation. It fixes the control rule and closure semantics.

## Linear-first Control Rule

The HONGSTR control baseline is:

`Initiate -> Register in Linear -> Execute -> Track -> Close`

Formal work must not bypass the `Register in Linear` step.

Supporting repo paths:

- [`docs/governance/ccpm_adoption.md`](/Users/hong/Projects/HONGSTR/docs/governance/ccpm_adoption.md)
- [`.github/ISSUE_TEMPLATE/task.yml`](/Users/hong/Projects/HONGSTR/.github/ISSUE_TEMPLATE/task.yml)
- [`docs/skills/hongstr-dev/pr_ssot_flow.md`](/Users/hong/Projects/HONGSTR/docs/skills/hongstr-dev/pr_ssot_flow.md)

## Mainline / Sandbox / Candidate Classification

### Mainline

- Has a Linear item
- Has an explicit execution path
- May proceed to PR and merge if acceptance evidence is satisfied

### Sandbox

- Must still be registered in Linear
- Must not be represented as mainline implementation
- Must not silently drift into formal execution without reclassification

### Candidate

- Worth tracking but not yet approved for mainline execution
- May later become mainline, deferred, superseded, or sandbox-only

## Orphan Work Forbidden

- Formal execution without a Linear item is forbidden.
- Sandbox without tracking is forbidden.
- Closure without a tracked issue is forbidden.
- If a work item cannot map to a valid card, it must stop and go through intake first.

## Closure Outcome Rule

Each tracked item must end in one of these closure outcomes:

- `DONE`
- `REJECT`
- `DEFERRED`
- `SANDBOX ONLY`
- `MERGED`
- `SUPERSEDED`

The exact state label may vary by platform, but every work item must have a closure path and a recorded outcome.

## Agent / Platform Alignment

This rule aligns:

- GitHub issue-driven CCPM governance
- Linear tracking
- agent branch / PR workflow
- repo-backed closure evidence

No agent should treat untracked work as formally executable.

## Acceptance Verdict

This package, together with the merged control-flow sources below, is the repo-backed owner acceptance package for `HONG-43`:

- PR `#77` / merge commit `609367055552891ecae9dd6bf50afeba4cc7b633`
- PR `#180` / merge commit `264362df7d6d4d30c484109aac6426ab2a4354bd`
- PR `#303` / merge commit `a77a6d76b140afd45c436f494810efb5c6b3b5c3`

Primary supporting paths:

- [`docs/governance/ccpm_adoption.md`](/Users/hong/Projects/HONGSTR/docs/governance/ccpm_adoption.md)
- [`.github/ISSUE_TEMPLATE/task.yml`](/Users/hong/Projects/HONGSTR/.github/ISSUE_TEMPLATE/task.yml)
- [`docs/skills/hongstr-dev/pr_ssot_flow.md`](/Users/hong/Projects/HONGSTR/docs/skills/hongstr-dev/pr_ssot_flow.md)

With this package merged, `HONG-43` can be treated as owner-package complete.
