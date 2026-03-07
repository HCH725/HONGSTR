# Seed Registry Sync Contract

This document closes the last `seed issue / registry sync contract` blocker for `HONG-5`.

## Canonical Contract Snapshot

```json
{
  "artifact_id": "seed_registry_sync_contract.v1",
  "canonical_upstreams": [
    "docs/governance/stage_registry.v1.json",
    "docs/governance/stage_registry_mapping.v1.json",
    "docs/governance/stage_rollup_policy.v1.json"
  ],
  "sync_scope": {
    "seed_cards": ["HONG-5", "HONG-18", "HONG-50"],
    "stage_cards": ["HONG-21", "HONG-22", "HONG-23"],
    "owner_cards": ["HONG-35", "HONG-36", "HONG-43"],
    "consumer_cards": ["HONG-15", "HONG-24"]
  },
  "discrepancy_rule": {
    "canonical_precedence": "repo_governance_paths_win",
    "linear_mismatch_action": "reopen_or_hold_seed_card_until_reconciled",
    "consumer_summary_action": "downgrade_to_reference_only_until_recomputed"
  },
  "evidence_rule": {
    "accepted_evidence_types": [
      "merged_pr",
      "merge_commit",
      "repo_path",
      "canonical_path",
      "validator_test_result"
    ],
    "synced_requires": ["merged_pr", "merge_commit", "repo_path"],
    "unsynced_when": [
      "missing_repo_backed_evidence",
      "linear_state_mismatch",
      "stale_narrative_claim"
    ]
  },
  "review_trigger_rule": {
    "triggers": [
      "merged_governance_pr",
      "canonical_path_change",
      "linear_state_change",
      "validator_failure"
    ],
    "update_targets": ["HONG-5", "HONG-18", "HONG-50"],
    "discrepancy_log_path": "docs/governance/p0_tail_closure_audit.md"
  }
}
```

## Scope

- `HONG-21`, `HONG-22`, and `HONG-23` remain the only canonical upstreams for registry, mapping, and rollup semantics.
- `HONG-5`, `HONG-18`, and `HONG-50` are seed/controller cards that must reflect those upstreams and must not override them.
- `HONG-35`, `HONG-36`, and `HONG-43` stay owner-package cards whose completion state must remain aligned with repo-backed evidence.
- `HONG-15` and `HONG-24` stay consumer summaries only and must not become independent truth sources.

## Discrepancy Handling

- If Linear and repo disagree, the repo-backed canonical path wins.
- If a seed/controller card claims `Done` without merged repo-backed evidence, that card must be reopened or held open.
- If a consumer summary drifts from upstream registry/mapping/rollup artifacts, it must be downgraded to reference-only until recomputed.

## Evidence Rule

- `synced` requires a merged PR, merge commit, and the referenced repo path to exist.
- `unsynced` applies when evidence is missing, the Linear state does not match the merged repo state, or stale narrative survives after reconciliation.
- Comments and discussions may explain the mismatch, but they do not replace repo-backed evidence.

## Review Trigger

- Review this contract whenever a merged governance PR changes the upstream canonical paths, a Linear state changes on a covered seed/controller card, or a validator/test fails.
- Record discrepancies and closure updates in [`docs/governance/p0_tail_closure_audit.md`](/Users/hong/Projects/HONGSTR/docs/governance/p0_tail_closure_audit.md).
