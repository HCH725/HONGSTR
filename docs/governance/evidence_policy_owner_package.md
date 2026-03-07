# Evidence Policy Owner Package

## Purpose

This package closes the owner-card acceptance gap for `HONG-36`.

It does not replace existing acceptance-criteria guidance. The operational AC guide remains:

- [`docs/governance/acceptance_criteria.md`](/Users/hong/Projects/HONGSTR/docs/governance/acceptance_criteria.md)

This package fixes the owner-card requirements for evidence strength and closure semantics.

## Evidence Level Dictionary

### Level A — Strong implementation evidence

- merged PR
- merge commit / commit SHA
- machine-checkable validation or test result
- repo artifact with traced merge source

Level A can directly support `DONE`.

### Level B — Structural evidence

- repo file path
- workflow, template, or guardrail path
- parent or child governance-card linkage backed by repo evidence

Level B can support governance readiness or partial completion, but not implementation-complete by itself.

### Level C — SSOT evidence

- canonical path or key inside a fixed schema / contract / policy artifact
- state or policy path-key that proves existence, not completion

Level C can support existence and policy alignment, but not implementation-complete by itself.

### Level D — Discussion / intent evidence

- chat discussion
- planning-only text
- unmerged drafts
- oral confirmation without repo or merge trace

Level D must not support `DONE`.

## DONE Gate Rules

- Implementation-complete claims require Level A evidence.
- Level B or Level C evidence may support:
  - governance-only
  - structure-ready
  - provisional
  - TODO with explicit next action
- Level D evidence must not support `DONE`.
- If evidence sources conflict, the stronger and merged source wins; weaker conflicting narrative is downgraded.

## Governance-only vs Implementation-complete

### Governance-only

- Rule boundaries are explicit.
- Owners, risk, and downgrade paths are defined.
- Repo implementation may still be missing.

### Implementation-ready

- Scope and acceptance gates are clear enough to execute.
- This is still not implementation-complete.

### Implementation-complete

- The card has merged PR or commit evidence plus any required machine-checkable result.
- The evidence is repo-backed and traceable without relying on conversation memory.

## Upgrade / Downgrade Rules

### Upgrade

- A path-only or structure-only item can move upward only after merged PR or commit evidence is present.
- Governance cards can move to `Done` when an explicit owner acceptance package is merged and references the canonical source correctly.

### Downgrade

- A `Done` claim without strong evidence must be downgraded.
- Historical checklist text that is superseded by merged canonical artifacts becomes `historical reference only`.
- Discussion-only claims are always downgraded below `Done`.

## Evidence Source Baseline

Accepted source classes:

- merged PR #
- merge commit
- repo file path
- canonical path
- validator or test result
- explicit acceptance package

These classes are not equal in strength. The level rules above control what status they can support.

## Acceptance Verdict

This package, together with the merged evidence-policy sources below, is the repo-backed owner acceptance package for `HONG-36`:

- PR `#180` / merge commit `264362df7d6d4d30c484109aac6426ab2a4354bd`
- PR `#303` / merge commit `a77a6d76b140afd45c436f494810efb5c6b3b5c3`

Primary supporting paths:

- [`docs/governance/acceptance_criteria.md`](/Users/hong/Projects/HONGSTR/docs/governance/acceptance_criteria.md)
- [`docs/governance/p0_upper_layer_reconciliation.md`](/Users/hong/Projects/HONGSTR/docs/governance/p0_upper_layer_reconciliation.md)

With this package merged, `HONG-36` can be treated as owner-package complete.
