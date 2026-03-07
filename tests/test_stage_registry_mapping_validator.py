import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "governance" / "validate_stage_registry_mapping.py"
MAPPING = REPO / "docs" / "governance" / "stage_registry_mapping.v1.json"
REGISTRY = REPO / "docs" / "governance" / "stage_registry.v1.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage_registry_mapping_validator_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_stage_registry_mapping_baseline_passes_validation():
    mod = _load_module()
    mapping_payload = mod.load_json(MAPPING)
    registry_payload = mod.load_json(REGISTRY)
    assert mod.validate_mapping(mapping_payload, registry_payload, MAPPING, REGISTRY) == []


def test_stage_registry_mapping_rejects_duplicate_checklist_item_id():
    mod = _load_module()
    mapping_payload = mod.load_json(MAPPING)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload["entries"][1]["checklist_item_id"] = mapping_payload["entries"][0]["checklist_item_id"]

    errors = mod.validate_mapping(mapping_payload, registry_payload, MAPPING, REGISTRY)

    assert any("duplicate checklist_item_id" in error for error in errors)


def test_stage_registry_mapping_rejects_duplicate_registry_and_item_id():
    mod = _load_module()
    mapping_payload = mod.load_json(MAPPING)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload["entries"][2]["registry_id"] = mapping_payload["entries"][1]["registry_id"]
    mapping_payload["entries"][2]["item_id"] = mapping_payload["entries"][1]["item_id"]

    errors = mod.validate_mapping(mapping_payload, registry_payload, MAPPING, REGISTRY)

    assert any("duplicate registry_id" in error for error in errors)
    assert any("duplicate item_id" in error for error in errors)


def test_stage_registry_mapping_rejects_unknown_parent_id():
    mod = _load_module()
    mapping_payload = mod.load_json(MAPPING)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload["entries"][2]["parent_id"] = "P0-SREG-99"

    errors = mod.validate_mapping(mapping_payload, registry_payload, MAPPING, REGISTRY)

    assert any("parent_id references unknown item_id" in error for error in errors)


def test_stage_registry_mapping_rejects_invalid_naming():
    mod = _load_module()
    mapping_payload = mod.load_json(MAPPING)
    registry_payload = mod.load_json(REGISTRY)
    mapping_payload["entries"][3]["registry_id"] = "hong-23"

    errors = mod.validate_mapping(mapping_payload, registry_payload, MAPPING, REGISTRY)

    assert any("registry_id does not match HONG-21 naming rules" in error for error in errors)
