#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = REPO / "docs" / "governance" / "stage_rollup_policy.v1.json"
DEFAULT_REGISTRY_PATH = REPO / "docs" / "governance" / "stage_registry.v1.json"
DEFAULT_MAPPING_PATH = REPO / "docs" / "governance" / "stage_registry_mapping.v1.json"
REGISTRY_VALIDATOR_PATH = REPO / "scripts" / "governance" / "validate_stage_registry.py"
MAPPING_VALIDATOR_PATH = REPO / "scripts" / "governance" / "validate_stage_registry_mapping.py"
REQUIRED_POLICY_KEYS = [
    "inclusion_rule",
    "exclusion_rule",
    "done_count_rule",
    "todo_count_rule",
    "blocked_count_rule",
    "stage_rollup_rule",
    "aggregate_rollup_rule",
    "blocker_selection_rule",
    "top_next_action_rule",
    "evidence_gate_rule",
    "recompute_trigger_rule",
]
FORBIDDEN_REDEFINITION_KEYS = {
    "required_fields",
    "field_semantics",
    "allowed_layers",
    "allowed_status_semantics",
    "allowed_owner_planes",
    "allowed_evidence_types",
    "mapping_required_fields",
    "mapping_rule_dictionary",
    "naming_rules",
}


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_rollup_policy(
    policy_payload: dict[str, Any],
    registry_payload: dict[str, Any],
    mapping_payload: dict[str, Any],
    policy_path: Path | None = None,
    registry_path: Path | None = None,
    mapping_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []

    registry_validator = _load_module(REGISTRY_VALIDATOR_PATH, "stage_registry_validator_dep_rollup")
    mapping_validator = _load_module(MAPPING_VALIDATOR_PATH, "stage_registry_mapping_validator_dep_rollup")

    registry_errors = registry_validator.validate_registry(registry_payload, registry_path or DEFAULT_REGISTRY_PATH)
    if registry_errors:
        errors.append("dependent HONG-21 registry is invalid")
        errors.extend([f"registry::{error}" for error in registry_errors])
        return errors

    mapping_errors = mapping_validator.validate_mapping(
        mapping_payload,
        registry_payload,
        mapping_path or DEFAULT_MAPPING_PATH,
        registry_path or DEFAULT_REGISTRY_PATH,
    )
    if mapping_errors:
        errors.append("dependent HONG-22 mapping is invalid")
        errors.extend([f"mapping::{error}" for error in mapping_errors])
        return errors

    if policy_payload.get("artifact_id") != "stage_rollup_policy.v1":
        errors.append("artifact_id must be 'stage_rollup_policy.v1'")

    if policy_payload.get("depends_on_registry") != "docs/governance/stage_registry.v1.json":
        errors.append("depends_on_registry must point to docs/governance/stage_registry.v1.json")

    if policy_payload.get("depends_on_registry_artifact_id") != registry_payload.get("artifact_id"):
        errors.append("depends_on_registry_artifact_id must match stage_registry.v1")

    if policy_payload.get("depends_on_mapping") != "docs/governance/stage_registry_mapping.v1.json":
        errors.append("depends_on_mapping must point to docs/governance/stage_registry_mapping.v1.json")

    if policy_payload.get("depends_on_mapping_artifact_id") != mapping_payload.get("artifact_id"):
        errors.append("depends_on_mapping_artifact_id must match stage_registry_mapping.v1")

    for key in FORBIDDEN_REDEFINITION_KEYS:
        if key in policy_payload:
            errors.append(f"rollup policy must not redefine upstream key '{key}'")

    baseline = policy_payload.get("rollup_policy_baseline")
    if not isinstance(baseline, dict):
        errors.append("rollup_policy_baseline must be an object")
        return errors

    for key in REQUIRED_POLICY_KEYS:
        if key not in baseline:
            errors.append(f"rollup_policy_baseline missing '{key}'")

    if errors:
        return errors

    inclusion_rule = baseline["inclusion_rule"]
    exclusion_rule = baseline["exclusion_rule"]
    done_count_rule = baseline["done_count_rule"]
    todo_count_rule = baseline["todo_count_rule"]
    blocked_count_rule = baseline["blocked_count_rule"]
    stage_rollup_rule = baseline["stage_rollup_rule"]
    aggregate_rollup_rule = baseline["aggregate_rollup_rule"]
    blocker_selection_rule = baseline["blocker_selection_rule"]
    top_next_action_rule = baseline["top_next_action_rule"]
    evidence_gate_rule = baseline["evidence_gate_rule"]
    recompute_trigger_rule = baseline["recompute_trigger_rule"]

    allowed_layers = set(registry_payload.get("allowed_layers") or [])
    allowed_statuses = set(registry_payload.get("allowed_status_semantics") or [])
    allowed_evidence_types = set(registry_payload.get("allowed_evidence_types") or [])

    eligible_layers = inclusion_rule.get("eligible_layers")
    excluded_layers = exclusion_rule.get("excluded_layers")
    context_only_layers = exclusion_rule.get("context_only_layers")
    current_mainline_layers = stage_rollup_rule.get("current_mainline_layers")
    stage_context_layers = stage_rollup_rule.get("context_layers")

    for name, value in [
        ("eligible_layers", eligible_layers),
        ("excluded_layers", excluded_layers),
        ("context_only_layers", context_only_layers),
        ("current_mainline_layers", current_mainline_layers),
        ("stage_context_layers", stage_context_layers),
    ]:
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"{name} must be a list of strings")

    if errors:
        return errors

    eligible_layer_set = set(eligible_layers)
    excluded_layer_set = set(excluded_layers)
    context_only_layer_set = set(context_only_layers)
    current_mainline_layer_set = set(current_mainline_layers)
    stage_context_layer_set = set(stage_context_layers)

    if not eligible_layer_set.issubset(allowed_layers):
        errors.append("inclusion_rule eligible_layers must stay within HONG-21 allowed layers")
    if not excluded_layer_set.issubset(allowed_layers):
        errors.append("exclusion_rule excluded_layers must stay within HONG-21 allowed layers")
    if not context_only_layer_set.issubset(allowed_layers):
        errors.append("exclusion_rule context_only_layers must stay within HONG-21 allowed layers")

    if eligible_layer_set & excluded_layer_set:
        errors.append("inclusion_rule and exclusion_rule cannot target the same layer")
    if eligible_layer_set & context_only_layer_set:
        errors.append("eligible_layers and context_only_layers cannot overlap")
    if current_mainline_layer_set & stage_context_layer_set:
        errors.append("stage_rollup_rule current_mainline_layers and context_layers cannot overlap")

    if "Layer3" in eligible_layer_set:
        errors.append("Layer3 candidate backlog must not enter current mainline inclusion_rule")
    if "Layer3" not in excluded_layer_set:
        errors.append("Layer3 candidate backlog must be explicitly excluded")
    if "Layer4" not in context_only_layer_set:
        errors.append("Layer4 must remain context-only in exclusion_rule")

    if done_count_rule.get("evidence_gate") != "EVIDENCE_REQUIRED":
        errors.append("done_count_rule must require evidence gate")
    if set(done_count_rule.get("count_statuses") or []) != {"DONE"}:
        errors.append("done_count_rule must count DONE only")
    if set(todo_count_rule.get("count_statuses") or []) != {"TODO", "IN_PROGRESS"}:
        errors.append("todo_count_rule must count TODO and IN_PROGRESS")
    if set(blocked_count_rule.get("count_statuses") or []) != {"BLOCKED"}:
        errors.append("blocked_count_rule must count BLOCKED only")
    if blocked_count_rule.get("exclude_general_backlog") is not True:
        errors.append("blocked_count_rule must exclude general backlog from blocked counts")
    if "Layer4" not in set(blocked_count_rule.get("context_layers") or []):
        errors.append("blocked_count_rule must keep Layer4 as blocker context only")
    if "Layer3" not in set(blocker_selection_rule.get("exclude_layers") or []):
        errors.append("blocker_selection_rule must exclude Layer3 backlog items")
    if blocker_selection_rule.get("include_layer4_as_context_only") is not True:
        errors.append("blocker_selection_rule must treat Layer4 as context only")

    if aggregate_rollup_rule.get("source") != "stage_rollup":
        errors.append("aggregate_rollup_rule source must be stage_rollup")
    if set(aggregate_rollup_rule.get("sum_fields") or []) != {"done", "todo", "blocked"}:
        errors.append("aggregate_rollup_rule must sum done/todo/blocked only")
    if aggregate_rollup_rule.get("exclude_context_only_from_done_todo") is not True:
        errors.append("aggregate_rollup_rule must exclude context-only layers from done/todo sums")

    top_statuses = set(top_next_action_rule.get("eligible_statuses") or [])
    if not top_statuses or not top_statuses.issubset(allowed_statuses):
        errors.append("top_next_action_rule eligible_statuses must be a non-empty subset of HONG-21 status vocabulary")
    if top_next_action_rule.get("not_parent_child_hierarchy") is not True:
        errors.append("top_next_action_rule must explicitly reject parent-child hierarchy as selection logic")
    if "parent_id" not in set(top_next_action_rule.get("forbidden_source_fields") or []):
        errors.append("top_next_action_rule must forbid parent_id as a selection source")
    if top_next_action_rule.get("max_items") != 2:
        errors.append("top_next_action_rule must cap Top1/Top2 at 2 items")

    if evidence_gate_rule.get("done_requires_evidence") is not True:
        errors.append("evidence_gate_rule must require evidence before DONE")
    if set(evidence_gate_rule.get("allowed_evidence_types") or []) != allowed_evidence_types:
        errors.append("evidence_gate_rule allowed_evidence_types must match HONG-21 allowed evidence types")
    if evidence_gate_rule.get("downgrade_target_without_evidence") != "TODO":
        errors.append("evidence_gate_rule must downgrade insufficient evidence to TODO")

    triggers = recompute_trigger_rule.get("triggers")
    if not isinstance(triggers, list) or not all(isinstance(item, str) for item in triggers):
        errors.append("recompute_trigger_rule triggers must be a list of strings")
    elif not {"registry_change", "mapping_change", "rollup_policy_change", "status_change", "evidence_change", "blocker_change"}.issubset(set(triggers)):
        errors.append("recompute_trigger_rule must include registry/mapping/policy/status/evidence/blocker triggers")
    target_cards = recompute_trigger_rule.get("target_cards")
    if not isinstance(target_cards, list) or not all(isinstance(item, str) for item in target_cards):
        errors.append("recompute_trigger_rule target_cards must be a list of strings")
    elif set(target_cards) != {"HONG-15", "HONG-24"}:
        errors.append("recompute_trigger_rule target_cards must be exactly HONG-15 and HONG-24")
    if recompute_trigger_rule.get("requires_full_recompute") is not True:
        errors.append("recompute_trigger_rule must require full recompute")

    return errors


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    policy_path = Path(argv[0]).resolve() if argv else DEFAULT_POLICY_PATH
    registry_path = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_REGISTRY_PATH
    mapping_path = Path(argv[2]).resolve() if len(argv) > 2 else DEFAULT_MAPPING_PATH

    policy_payload = load_json(policy_path)
    registry_payload = load_json(registry_path)
    mapping_payload = load_json(mapping_path)
    errors = validate_rollup_policy(policy_payload, registry_payload, mapping_payload, policy_path, registry_path, mapping_path)
    if errors:
        print("FAIL: stage rollup policy validation failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"PASS: stage rollup policy validation ok ({policy_path.relative_to(REPO).as_posix()})")
    print(f"PASS: validated {len(policy_payload['rollup_policy_baseline'])} policy keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
