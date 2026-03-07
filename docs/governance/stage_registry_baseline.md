# Stage Registry v1 Baseline

## Canonical SSOT

- Canonical artifact: [`docs/governance/stage_registry.v1.json`](/Users/hong/Projects/HONGSTR/docs/governance/stage_registry.v1.json)
- Owner card: `HONG-21` (`P0-SREG-01`)
- Purpose: provide the single schema and vocabulary baseline for Stage Registry work.

## Stage Registry Schema

The canonical JSON artifact fixes the required field set for downstream registry entries:

- `stage_id`
- `stage_name`
- `registry_id`
- `item_id`
- `item_title`
- `layer`
- `owner_plane`
- `status_semantics`
- `evidence_type`
- `evidence_ref`
- `degrade_rule`
- `kill_switch`
- `blocked_by`
- `next_action`

## Registry SSOT Role

- `stage_registry.v1.json` is the only repo-backed schema baseline for `HONG-21`.
- `HONG-22` and `HONG-23` must attach to this artifact instead of redefining field names or status/layer vocabularies elsewhere.
- This baseline is machine-checkable and must stay valid before downstream mapping or rollup work can claim completion.

## Allowed Status Vocabulary

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

These values are fixed for the v1 baseline. Downstream cards may consume them, but must not rename them in a conflicting registry.

## Layer Semantics Contract

- `Layer1`: Master / WBS / Rollup
- `Layer2`: Current Mainline Buildout
- `Layer3`: Candidate Backlog
- `Layer4`: Delayed / Blocker-sensitive Work

The layer vocabulary is fixed in `stage_registry.v1.json` and validated by the registry checker.

## Validation

Run either command from the repo root:

```bash
python3 scripts/governance/validate_stage_registry.py
python3 -m pytest -q tests/test_stage_registry_validator.py
```

Both commands must pass before `HONG-21` can move forward.

## Out of Scope in This PR

- `HONG-22` checklist mapping rules
- `HONG-23` rollup policy
- Any runtime code change under `src/hongstr/**`

This PR only establishes the schema baseline and canonical SSOT path. It does not claim mapping-complete or rollup-complete delivery.
