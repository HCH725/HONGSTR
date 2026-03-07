# Red Lines SSOT Owner Package

## Purpose

This package closes the owner-card acceptance gap for `HONG-35`.

It does not replace the policy SSOT. The canonical red-lines policy remains:

- [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md)

This package exists to make the owner-card requirements explicit, traceable, and closure-ready.

## Canonical Red Lines List

1. `src/hongstr/**` core-path protection
   - Source: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md)
2. `core diff = 0` baseline
   - Source: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md)
3. SSOT writer boundary
   - Sources: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md), [`scripts/check_state_writer_boundary.py`](/Users/hong/Projects/HONGSTR/scripts/check_state_writer_boundary.py)
4. P0 deterministic baseline
   - Sources: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md), [`docs/governance/p0_upper_layer_reconciliation.md`](/Users/hong/Projects/HONGSTR/docs/governance/p0_upper_layer_reconciliation.md)
5. `tg_cp` / control-plane read-only / no-exec
   - Sources: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md), [`_local/telegram_cp/tg_cp_server.py`](/Users/hong/Projects/HONGSTR/_local/telegram_cp/tg_cp_server.py)
6. dashboard / `/status` / `/daily` SSOT-only consumption
   - Source class: governance and SSOT policies, not ad hoc consumer fallback
7. research / ML `report_only` baseline
   - Sources: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md), [`docs/governance/ccpm_adoption.md`](/Users/hong/Projects/HONGSTR/docs/governance/ccpm_adoption.md)
8. no generated artifacts in git
   - Sources: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md), [`scripts/guardrail_check.sh`](/Users/hong/Projects/HONGSTR/scripts/guardrail_check.sh)
9. secrets never in repo
   - Sources: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md), [`.github/workflows/ci.yml`](/Users/hong/Projects/HONGSTR/.github/workflows/ci.yml)
10. Telegram-only operational channel baseline
   - Sources: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md), [`_local/telegram_cp/tg_cp_server.py`](/Users/hong/Projects/HONGSTR/_local/telegram_cp/tg_cp_server.py)
11. no dual truth between repo / state / control surfaces
   - Source: [`docs/governance/p0_upper_layer_reconciliation.md`](/Users/hong/Projects/HONGSTR/docs/governance/p0_upper_layer_reconciliation.md)
12. sandbox-first rule for unmapped work
   - Sources: [`docs/governance/p0_upper_layer_reconciliation.md`](/Users/hong/Projects/HONGSTR/docs/governance/p0_upper_layer_reconciliation.md), [`docs/governance/linear_first_control_package.md`](/Users/hong/Projects/HONGSTR/docs/governance/linear_first_control_package.md)

## Hard Stop vs Degrade vs Escalation

### Hard Stop

- Any write under `src/hongstr/**` without explicit authorization
- Any committed runtime artifact under `data/**` or binary model/output files
- Any control-plane execution path that breaks read-only / no-exec
- Any secret or credential committed into the repo

### Degrade

- Research or analysis work that cannot yet prove `report_only`
- Consumer summaries that drift from canonical SSOT sources
- Governance cards that have path-only evidence but no explicit owner package

### Escalation

- Conflicting interpretations of the same red line
- Conflicting SSOTs between repo policy, state policy, and control surfaces
- Work that cannot map to an existing checklist or owner rule and therefore must not bypass sandbox-first handling

## Red Line Evidence Sources

Accepted evidence sources for red-lines governance:

- merged PRs and merge commits
- repo policy files under `docs/**`
- guardrail and verification scripts under `scripts/**`
- SSOT governance notes under `docs/governance/**`
- Linear owner cards only when paired with repo-backed policy or merge evidence

Discussion-only evidence is not accepted for `HONG-35`.

## Acceptance Verdict

This package, together with the merged policy sources below, is the repo-backed owner acceptance package for `HONG-35`:

- PR `#51` / merge commit `0ae8dead05ebcf2f010b5bb9f77b57e690c8ebe7`
- PR `#72` / merge commit `5ee4ad93e5ad8e00b04b161eb416bf93a77abb82`
- PR `#192` / merge commit `d0c5bce3d2961ab76ab4b6f965072e40d18abb3a`
- PR `#303` / merge commit `a77a6d76b140afd45c436f494810efb5c6b3b5c3`

With this package merged, `HONG-35` can be treated as owner-package complete.
