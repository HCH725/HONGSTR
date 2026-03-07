# Red Line Drift Audit Cadence

This document closes the last `red-line drift audit cadence` blocker for `HONG-5`.

## Canonical Cadence Snapshot

```json
{
  "artifact_id": "red_line_drift_audit_cadence.v1",
  "owner_plane": "CONTROL",
  "audit_owner_cards": ["HONG-35", "HONG-5", "HONG-50"],
  "audit_cadence": "weekly",
  "review_artifact_paths": [
    "docs/governance/p0_tail_closure_audit.md",
    "docs/governance/red_lines_ssot_owner_package.md"
  ],
  "evidence_paths": [
    "docs/governance/red_lines_ssot_owner_package.md",
    "docs/governance/acceptance_criteria.md",
    "docs/governance/stage_registry.v1.json",
    "docs/governance/stage_registry_mapping.v1.json",
    "docs/governance/stage_rollup_policy.v1.json"
  ],
  "pass_fail_rule": {
    "pass_when": [
      "red_lines_match_canonical_repo_paths",
      "no_undocumented_drift",
      "required_evidence_present"
    ],
    "fail_when": [
      "undocumented_red_line_change",
      "missing_review_artifact",
      "evidence_gap_on_done_claim"
    ],
    "escalate_to": "P0_RISK"
  },
  "drift_response_rule": {
    "on_fail": [
      "reopen_HONG-5",
      "hold_HONG-50_open",
      "downgrade_affected_done_claims_to_todo"
    ],
    "requires_repo_backed_followup": true
  }
}
```

## Cadence

- Run this audit weekly.
- `owner_plane` is `CONTROL`.
- Use [`docs/governance/p0_tail_closure_audit.md`](/Users/hong/Projects/HONGSTR/docs/governance/p0_tail_closure_audit.md) as the reconciliation note and [`docs/governance/red_lines_ssot_owner_package.md`](/Users/hong/Projects/HONGSTR/docs/governance/red_lines_ssot_owner_package.md) as the red-line owner baseline.

## Pass / Fail Semantics

- Pass: canonical red-line paths still match the repo state, no undocumented drift exists, and `Done` claims still have required evidence.
- Fail: undocumented red-line drift exists, the review artifact is missing, or any `Done` claim lacks supporting evidence.
- Escalate failed audits as `P0_RISK`.

## Drift Handling

- On failure, reopen `HONG-5`, keep `HONG-50` open, and downgrade any affected `Done` claim to `TODO` until repo-backed follow-up evidence lands.
- This cadence does not create any runtime scheduler; it only fixes the governance review rhythm and its pass/fail semantics.
