import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "governance" / "validate_stage_registry.py"
REGISTRY = REPO / "docs" / "governance" / "stage_registry.v1.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage_registry_validator_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_stage_registry_baseline_passes_validation():
    mod = _load_module()
    payload = mod.load_registry(REGISTRY)
    assert mod.validate_registry(payload, REGISTRY) == []


def test_stage_registry_rejects_invalid_layer():
    mod = _load_module()
    payload = mod.load_registry(REGISTRY)
    payload["baseline_entries"][0]["layer"] = "Layer5"

    errors = mod.validate_registry(payload, REGISTRY)

    assert any("invalid layer" in error for error in errors)


def test_stage_registry_rejects_invalid_registry_id():
    mod = _load_module()
    payload = mod.load_registry(REGISTRY)
    payload["baseline_entries"][0]["registry_id"] = "hong-21"

    errors = mod.validate_registry(payload, REGISTRY)

    assert any("registry_id does not match" in error for error in errors)
