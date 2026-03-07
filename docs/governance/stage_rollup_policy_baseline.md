# Stage Rollup Policy v1 Baseline

## Canonical Rollup SSOT

- Canonical artifact: [`docs/governance/stage_rollup_policy.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_rollup_policy.v1.json)
- Registry dependency: [`docs/governance/stage_registry.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry.v1.json)
- Mapping dependency: [`docs/governance/stage_registry_mapping.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry_mapping.v1.json)
- Owner card: `HONG-23` (`P0-SREG-03`)

## Rollup Policy Scope

- `HONG-23` fixes rollup policy only.
- This artifact defines:
  - inclusion / exclusion rules
  - done / todo / blocked aggregation semantics
  - stage rollup / aggregate rollup rules
  - blocker / Top1 / Top2 selection rules
  - evidence gate
  - recompute trigger rule
- This artifact does **not** redefine HONG-21 schema vocabulary or HONG-22 mapping semantics.

## Dependency on HONG-21 / HONG-22

- The rollup validator loads the HONG-21 registry and HONG-22 mapping validators before accepting the policy artifact.
- `HONG-23` must not redefine `required_fields`, `allowed_layers`, `allowed_status_semantics`, `mapping_required_fields`, or `mapping_rule_dictionary`.
- `HONG-15` and `HONG-24` should later point to [`docs/governance/stage_rollup_policy.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_rollup_policy.v1.json) as their canonical rollup source.

## Top Action Selection Rule

- `Top1` / `Top2` are next-action priorities.
- They must not be interpreted as parent-child hierarchy.
- `parent_id` is explicitly forbidden as a Top1 / Top2 selection source.

## Validation

Run either command from the repo root:

```bash
python3 scripts/governance/validate_stage_rollup_policy.py
python3 -m pytest -q tests/test_stage_rollup_policy_validator.py
```

Both commands must pass before `HONG-23` can move forward.

## Out of Scope in This PR

- Any new stage registry schema vocabulary
- Any new checklist mapping semantics
- Any runtime code change under `src/hongstr/**`
- Any direct rewrite of HONG-15 / HONG-24 deliverables

This PR establishes the rollup policy baseline only. Downstream cards can reference it after merge.
