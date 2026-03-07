# P0 Upper-Layer Governance Reconciliation

## Purpose

This document closes the upper-layer governance gap after the Stage Registry foundation package was merged.

It does not create a new registry, mapping, or rollup artifact. It only records which existing canonical artifacts now govern:

- `HONG-18` machine-readable stage registry gap closure
- `HONG-15` Master Overview source references
- `HONG-24` WBS Index source references
- `HONG-50` remaining audit tail items

## Canonical Sources

The only canonical Stage Registry package is:

1. `HONG-21`
   - PR `#300`
   - merge commit `d909dc8a7f450d23ddfb89b211dd1d806eef9b75`
   - artifact: [`docs/governance/stage_registry.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry.v1.json)
2. `HONG-22`
   - PR `#301`
   - merge commit `0e2a1a02d67767b448a36db2cfafcc007e898bc7`
   - artifact: [`docs/governance/stage_registry_mapping.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry_mapping.v1.json)
3. `HONG-23`
   - PR `#302`
   - merge commit `d9815fee93bf8f333b58cd9525187db379bc883b`
   - artifact: [`docs/governance/stage_rollup_policy.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_rollup_policy.v1.json)

Supporting validators remain:

- [`scripts/governance/validate_stage_registry.py`](/Users/hong/Projects/HONGSTR/scripts/governance/validate_stage_registry.py)
- [`scripts/governance/validate_stage_registry_mapping.py`](/Users/hong/Projects/HONGSTR/scripts/governance/validate_stage_registry_mapping.py)
- [`scripts/governance/validate_stage_rollup_policy.py`](/Users/hong/Projects/HONGSTR/scripts/governance/validate_stage_rollup_policy.py)

## HONG-18 Closure Rule

`HONG-18` exists to close the machine-readable stage registry gap.

That gap is now closed by the merged `HONG-21` + `HONG-22` + `HONG-23` package:

- schema baseline exists
- checklist-to-registry mapping exists
- rollup policy exists
- machine-checkable validators and tests exist

`HONG-18` should therefore point to the three merged artifacts above as its closure evidence instead of continuing to describe the gap as open.

## HONG-15 Consumer Rule

`HONG-15` is a Master Overview consumer and narrative control card. It is not a new source of truth for:

- stage registry structure
- checklist mapping semantics
- rollup policy semantics

`HONG-15` must cite these canonical sources:

- [`docs/governance/stage_registry.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry.v1.json)
- [`docs/governance/stage_registry_mapping.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry_mapping.v1.json)
- [`docs/governance/stage_rollup_policy.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_rollup_policy.v1.json)

Legacy narrative inside `HONG-15` is downgraded to reference-only when it overlaps with those canonical artifacts. This includes:

- any `Rollup Policy (draft)` placeholder wording
- any stage or aggregate rollup numbers not recomputed from the merged policy package
- any wording that implies `HONG-15` defines its own rollup formula

## HONG-24 Consumer Rule

`HONG-24` is a WBS / layer / navigation consumer and narrative summary card. It is not a hidden source of truth for:

- stage registry schema
- mapping semantics
- rollup semantics

`HONG-24` must cite the same canonical source package used by `HONG-15`.

Legacy WBS narrative remains useful for navigation, but it is reference-only whenever it overlaps with canonical registry, mapping, or rollup logic.

## HONG-50 Tail Rule

`HONG-50` should record that `HONG-21`, `HONG-22`, and `HONG-23` are all merged.

`HONG-50` may stay open only for remaining audit and closure work outside the finished Stage Registry foundation package, such as:

- `HONG-5` evidence downgrade and checklist correction
- unresolved owner-card acceptance packages such as `HONG-35`, `HONG-36`, and `HONG-43`
- any remaining upper-layer status reconciliation not yet updated in Linear

`HONG-50` should not continue to describe the Stage Registry package as missing.

## Validation

Run from the repo root:

```bash
python3 scripts/governance/validate_stage_registry.py
python3 scripts/governance/validate_stage_registry_mapping.py
python3 scripts/governance/validate_stage_rollup_policy.py
```

If those commands pass, the canonical package remains valid. This reconciliation document adds no new acceptance logic.
