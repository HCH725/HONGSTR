# Stage Registry Mapping v1 Baseline

## Canonical Mapping SSOT

- Canonical artifact: [`docs/governance/stage_registry_mapping.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry_mapping.v1.json)
- Registry dependency: [`docs/governance/stage_registry.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry.v1.json)
- Owner card: `HONG-22` (`P0-SREG-02`)

## Mapping Rule Scope

- `HONG-22` fixes checklist-to-registry mapping only.
- This baseline maps:
  - `checklist_item_id -> registry_id`
  - `registry_id -> item_id`
  - `item_id -> stage_id / layer / owner_plane / parent_id`
  - `item_id -> next_action_ref / blocked_by_ref`
- This artifact does **not** define rollup formulas, inclusion rules, or Top1/Top2 selection logic. Those remain `HONG-23`.

## Dependency on HONG-21

- `stage_registry_mapping.v1.json` must depend on the HONG-21 canonical registry at [`docs/governance/stage_registry.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry.v1.json).
- The mapping validator loads the HONG-21 registry and its validator before accepting the mapping artifact.
- `HONG-22` must not redefine the HONG-21 schema vocabulary (`required_fields`, `allowed_layers`, `allowed_status_semantics`, or naming regexes).

## Parent / Child Mapping Rules

- Every child item can point to only one `parent_id`.
- `parent_id` is structural lineage only; it is not a scheduling or prioritization signal.
- `Top1` / `Top2` are next-action priorities and must not be interpreted as parent-child hierarchy.

## Validation

Run either command from the repo root:

```bash
python3 scripts/governance/validate_stage_registry_mapping.py
python3 -m pytest -q tests/test_stage_registry_mapping_validator.py
```

Both commands must pass before `HONG-22` can move forward.

## Out of Scope in This PR

- `HONG-23` rollup policy
- Any new stage registry schema vocabulary
- Any runtime code change under `src/hongstr/**`

This PR establishes the canonical mapping baseline only. Rollup remains downstream work.
