import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "governance" / "validate_p0_closure_contracts.py"
SEED_CONTRACT = REPO / "docs" / "governance" / "seed_registry_sync_contract.md"
DRIFT_CADENCE = REPO / "docs" / "governance" / "red_line_drift_audit_cadence.md"
TAIL_AUDIT = REPO / "docs" / "governance" / "p0_tail_closure_audit.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("p0_closure_contracts_validator_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_p0_closure_contracts_baseline_passes_validation():
    mod = _load_module()
    seed_payload = mod.extract_snapshot(SEED_CONTRACT)
    drift_payload = mod.extract_snapshot(DRIFT_CADENCE)
    tail_audit_text = mod.load_markdown(TAIL_AUDIT)

    assert mod.validate_seed_registry_sync_contract(seed_payload) == []
    assert mod.validate_red_line_drift_audit_cadence(drift_payload) == []
    assert mod.validate_tail_audit_closure(tail_audit_text) == []


def test_seed_registry_sync_contract_rejects_missing_upstream():
    mod = _load_module()
    seed_payload = mod.extract_snapshot(SEED_CONTRACT)
    seed_payload["canonical_upstreams"] = ["docs/governance/stage_registry.v1.json"]

    errors = mod.validate_seed_registry_sync_contract(seed_payload)

    assert any("canonical_upstreams must match" in error for error in errors)


def test_seed_registry_sync_contract_rejects_wrong_update_targets():
    mod = _load_module()
    seed_payload = mod.extract_snapshot(SEED_CONTRACT)
    seed_payload["review_trigger_rule"]["update_targets"] = ["HONG-5"]

    errors = mod.validate_seed_registry_sync_contract(seed_payload)

    assert any("update_targets must be HONG-5/HONG-18/HONG-50" in error for error in errors)


def test_red_line_drift_cadence_rejects_invalid_owner_plane():
    mod = _load_module()
    drift_payload = mod.extract_snapshot(DRIFT_CADENCE)
    drift_payload["owner_plane"] = "EXECUTION"

    errors = mod.validate_red_line_drift_audit_cadence(drift_payload)

    assert any("owner_plane must be CONTROL" in error for error in errors)


def test_red_line_drift_cadence_rejects_missing_on_fail_action():
    mod = _load_module()
    drift_payload = mod.extract_snapshot(DRIFT_CADENCE)
    drift_payload["drift_response_rule"]["on_fail"] = ["reopen_HONG-5"]

    errors = mod.validate_red_line_drift_audit_cadence(drift_payload)

    assert any("on_fail must include the HONG-5/HONG-50/todo actions" in error for error in errors)


def test_tail_audit_requires_closure_snippets():
    mod = _load_module()
    tail_text = mod.load_markdown(TAIL_AUDIT).replace("`HONG-50` can move to `Done`", "")

    errors = mod.validate_tail_audit_closure(tail_text)

    assert any("missing '`HONG-50` can move to `Done`'" in error for error in errors)
