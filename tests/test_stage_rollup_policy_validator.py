import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "governance" / "validate_stage_rollup_policy.py"
POLICY = REPO / "docs" / "governance" / "stage_rollup_policy.v1.json"
REGISTRY = REPO / "docs" / "governance" / "stage_registry.v1.json"
MAPPING = REPO / "docs" / "governance" / "stage_registry_mapping.v1.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage_rollup_policy_validator_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_stage_rollup_policy_baseline_passes_validation():
    mod = _load_module()
    policy_payload = mod.load_json(POLICY)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload = mod.load_json(MAPPING)
    assert mod.validate_rollup_policy(policy_payload, registry_payload, mapping_payload, POLICY, REGISTRY, MAPPING) == []


def test_stage_rollup_policy_rejects_missing_policy_key():
    mod = _load_module()
    policy_payload = mod.load_json(POLICY)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload = mod.load_json(MAPPING)
    del policy_payload["rollup_policy_baseline"]["aggregate_rollup_rule"]

    errors = mod.validate_rollup_policy(policy_payload, registry_payload, mapping_payload, POLICY, REGISTRY, MAPPING)

    assert any("missing 'aggregate_rollup_rule'" in error for error in errors)


def test_stage_rollup_policy_rejects_inclusion_exclusion_conflict():
    mod = _load_module()
    policy_payload = mod.load_json(POLICY)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload = mod.load_json(MAPPING)
    policy_payload["rollup_policy_baseline"]["inclusion_rule"]["eligible_layers"].append("Layer3")

    errors = mod.validate_rollup_policy(policy_payload, registry_payload, mapping_payload, POLICY, REGISTRY, MAPPING)

    assert any("Layer3 candidate backlog must not enter current mainline inclusion_rule" in error for error in errors)


def test_stage_rollup_policy_rejects_evidence_gate_regression():
    mod = _load_module()
    policy_payload = mod.load_json(POLICY)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload = mod.load_json(MAPPING)
    policy_payload["rollup_policy_baseline"]["evidence_gate_rule"]["done_requires_evidence"] = False

    errors = mod.validate_rollup_policy(policy_payload, registry_payload, mapping_payload, POLICY, REGISTRY, MAPPING)

    assert any("must require evidence before DONE" in error for error in errors)


def test_stage_rollup_policy_rejects_missing_recompute_target_card():
    mod = _load_module()
    policy_payload = mod.load_json(POLICY)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload = mod.load_json(MAPPING)
    policy_payload["rollup_policy_baseline"]["recompute_trigger_rule"]["target_cards"] = ["HONG-15"]

    errors = mod.validate_rollup_policy(policy_payload, registry_payload, mapping_payload, POLICY, REGISTRY, MAPPING)

    assert any("target_cards must be exactly HONG-15 and HONG-24" in error for error in errors)


def test_stage_rollup_policy_rejects_top_action_parent_hierarchy():
    mod = _load_module()
    policy_payload = mod.load_json(POLICY)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload = mod.load_json(MAPPING)
    policy_payload["rollup_policy_baseline"]["top_next_action_rule"]["not_parent_child_hierarchy"] = False

    errors = mod.validate_rollup_policy(policy_payload, registry_payload, mapping_payload, POLICY, REGISTRY, MAPPING)

    assert any("must explicitly reject parent-child hierarchy" in error for error in errors)
