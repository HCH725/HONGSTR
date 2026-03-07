#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
SEED_CONTRACT_PATH = REPO / "docs" / "governance" / "seed_registry_sync_contract.md"
DRIFT_CADENCE_PATH = REPO / "docs" / "governance" / "red_line_drift_audit_cadence.md"
TAIL_AUDIT_PATH = REPO / "docs" / "governance" / "p0_tail_closure_audit.md"
JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
EXPECTED_UPSTREAMS = {
    "docs/governance/stage_registry.v1.json",
    "docs/governance/stage_registry_mapping.v1.json",
    "docs/governance/stage_rollup_policy.v1.json",
}


def load_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_snapshot(path: Path) -> dict[str, Any]:
    text = load_markdown(path)
    match = JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError(f"{path.relative_to(REPO).as_posix()} must contain one fenced json snapshot")
    return json.loads(match.group(1))


def _existing_repo_paths(paths: list[str], errors: list[str], label: str) -> None:
    for raw_path in paths:
        repo_path = REPO / raw_path
        if not repo_path.exists():
            errors.append(f"{label} references missing path '{raw_path}'")


def validate_seed_registry_sync_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if payload.get("artifact_id") != "seed_registry_sync_contract.v1":
        errors.append("artifact_id must be 'seed_registry_sync_contract.v1'")

    canonical_upstreams = payload.get("canonical_upstreams")
    if not isinstance(canonical_upstreams, list):
        errors.append("canonical_upstreams must be a list")
        canonical_upstreams = []
    elif set(canonical_upstreams) != EXPECTED_UPSTREAMS:
        errors.append("canonical_upstreams must match HONG-21/HONG-22/HONG-23 canonical paths exactly")
    _existing_repo_paths([path for path in canonical_upstreams if isinstance(path, str)], errors, "canonical_upstreams")

    sync_scope = payload.get("sync_scope")
    required_scope = {
        "seed_cards": {"HONG-5", "HONG-18", "HONG-50"},
        "stage_cards": {"HONG-21", "HONG-22", "HONG-23"},
        "owner_cards": {"HONG-35", "HONG-36", "HONG-43"},
        "consumer_cards": {"HONG-15", "HONG-24"},
    }
    if not isinstance(sync_scope, dict):
        errors.append("sync_scope must be an object")
        sync_scope = {}
    for scope_key, expected in required_scope.items():
        value = sync_scope.get(scope_key)
        if not isinstance(value, list):
            errors.append(f"sync_scope.{scope_key} must be a list")
            continue
        if set(value) != expected:
            errors.append(f"sync_scope.{scope_key} must match {sorted(expected)} exactly")

    discrepancy_rule = payload.get("discrepancy_rule")
    if not isinstance(discrepancy_rule, dict):
        errors.append("discrepancy_rule must be an object")
    else:
        if discrepancy_rule.get("canonical_precedence") != "repo_governance_paths_win":
            errors.append("discrepancy_rule canonical_precedence must be repo_governance_paths_win")
        for key in ["linear_mismatch_action", "consumer_summary_action"]:
            value = discrepancy_rule.get(key)
            if not isinstance(value, str) or len(value.strip()) < 10:
                errors.append(f"discrepancy_rule.{key} must be a meaningful string")

    evidence_rule = payload.get("evidence_rule")
    if not isinstance(evidence_rule, dict):
        errors.append("evidence_rule must be an object")
    else:
        accepted = evidence_rule.get("accepted_evidence_types")
        if not isinstance(accepted, list) or set(accepted) != {
            "merged_pr",
            "merge_commit",
            "repo_path",
            "canonical_path",
            "validator_test_result",
        }:
            errors.append("accepted_evidence_types must match the P0 closure evidence set exactly")
        synced_requires = evidence_rule.get("synced_requires")
        if not isinstance(synced_requires, list) or set(synced_requires) != {"merged_pr", "merge_commit", "repo_path"}:
            errors.append("synced_requires must require merged_pr/merge_commit/repo_path")
        unsynced_when = evidence_rule.get("unsynced_when")
        if not isinstance(unsynced_when, list) or "stale_narrative_claim" not in unsynced_when:
            errors.append("unsynced_when must include stale_narrative_claim")

    review_trigger_rule = payload.get("review_trigger_rule")
    if not isinstance(review_trigger_rule, dict):
        errors.append("review_trigger_rule must be an object")
    else:
        triggers = review_trigger_rule.get("triggers")
        if not isinstance(triggers, list) or not {
            "merged_governance_pr",
            "canonical_path_change",
            "linear_state_change",
            "validator_failure",
        }.issubset(set(triggers)):
            errors.append("review_trigger_rule triggers must include governance/path/state/validator triggers")
        targets = review_trigger_rule.get("update_targets")
        if not isinstance(targets, list) or set(targets) != {"HONG-5", "HONG-18", "HONG-50"}:
            errors.append("review_trigger_rule update_targets must be HONG-5/HONG-18/HONG-50")
        discrepancy_log_path = review_trigger_rule.get("discrepancy_log_path")
        if discrepancy_log_path != "docs/governance/p0_tail_closure_audit.md":
            errors.append("review_trigger_rule discrepancy_log_path must point to docs/governance/p0_tail_closure_audit.md")
        elif not (REPO / discrepancy_log_path).exists():
            errors.append("review_trigger_rule discrepancy_log_path must exist")

    return errors


def validate_red_line_drift_audit_cadence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if payload.get("artifact_id") != "red_line_drift_audit_cadence.v1":
        errors.append("artifact_id must be 'red_line_drift_audit_cadence.v1'")
    if payload.get("owner_plane") != "CONTROL":
        errors.append("owner_plane must be CONTROL")
    if payload.get("audit_cadence") != "weekly":
        errors.append("audit_cadence must be weekly")

    owner_cards = payload.get("audit_owner_cards")
    if not isinstance(owner_cards, list) or set(owner_cards) != {"HONG-35", "HONG-5", "HONG-50"}:
        errors.append("audit_owner_cards must be HONG-35/HONG-5/HONG-50")

    review_artifact_paths = payload.get("review_artifact_paths")
    if not isinstance(review_artifact_paths, list) or {
        "docs/governance/p0_tail_closure_audit.md",
        "docs/governance/red_lines_ssot_owner_package.md",
    } - set(review_artifact_paths):
        errors.append("review_artifact_paths must include p0_tail_closure_audit.md and red_lines_ssot_owner_package.md")
        review_artifact_paths = []
    _existing_repo_paths([path for path in review_artifact_paths if isinstance(path, str)], errors, "review_artifact_paths")

    evidence_paths = payload.get("evidence_paths")
    expected_evidence_paths = {
        "docs/governance/red_lines_ssot_owner_package.md",
        "docs/governance/acceptance_criteria.md",
        "docs/governance/stage_registry.v1.json",
        "docs/governance/stage_registry_mapping.v1.json",
        "docs/governance/stage_rollup_policy.v1.json",
    }
    if not isinstance(evidence_paths, list) or set(evidence_paths) != expected_evidence_paths:
        errors.append("evidence_paths must match the red-line governance evidence set exactly")
        evidence_paths = []
    _existing_repo_paths([path for path in evidence_paths if isinstance(path, str)], errors, "evidence_paths")

    pass_fail_rule = payload.get("pass_fail_rule")
    if not isinstance(pass_fail_rule, dict):
        errors.append("pass_fail_rule must be an object")
    else:
        if pass_fail_rule.get("escalate_to") != "P0_RISK":
            errors.append("pass_fail_rule escalate_to must be P0_RISK")
        for key, expected_member in [
            ("pass_when", "required_evidence_present"),
            ("fail_when", "evidence_gap_on_done_claim"),
        ]:
            value = pass_fail_rule.get(key)
            if not isinstance(value, list) or expected_member not in value:
                errors.append(f"pass_fail_rule.{key} must include {expected_member}")

    drift_response_rule = payload.get("drift_response_rule")
    if not isinstance(drift_response_rule, dict):
        errors.append("drift_response_rule must be an object")
    else:
        on_fail = drift_response_rule.get("on_fail")
        if not isinstance(on_fail, list) or not {
            "reopen_HONG-5",
            "hold_HONG-50_open",
            "downgrade_affected_done_claims_to_todo",
        }.issubset(set(on_fail)):
            errors.append("drift_response_rule on_fail must include the HONG-5/HONG-50/todo actions")
        if drift_response_rule.get("requires_repo_backed_followup") is not True:
            errors.append("drift_response_rule requires_repo_backed_followup must be true")

    return errors


def validate_tail_audit_closure(text: str) -> list[str]:
    errors: list[str] = []
    required_snippets = [
        "seed_registry_sync_contract.md",
        "red_line_drift_audit_cadence.md",
        "`HONG-5` can move to `Done`",
        "`HONG-50` can move to `Done`",
    ]
    for snippet in required_snippets:
        if snippet not in text:
            errors.append(f"p0_tail_closure_audit.md missing '{snippet}'")
    return errors


def main(argv: list[str] | None = None) -> int:
    _ = argv or sys.argv[1:]
    seed_payload = extract_snapshot(SEED_CONTRACT_PATH)
    drift_payload = extract_snapshot(DRIFT_CADENCE_PATH)
    tail_audit_text = load_markdown(TAIL_AUDIT_PATH)

    errors = []
    errors.extend(validate_seed_registry_sync_contract(seed_payload))
    errors.extend(validate_red_line_drift_audit_cadence(drift_payload))
    errors.extend(validate_tail_audit_closure(tail_audit_text))

    if errors:
        print("FAIL: P0 closure contract validation failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print("PASS: P0 closure contract validation ok")
    print("PASS: validated seed sync contract, red-line drift cadence, and tail closure audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
