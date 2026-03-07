#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_MAPPING_PATH = REPO / "docs" / "governance" / "stage_registry_mapping.v1.json"
DEFAULT_REGISTRY_PATH = REPO / "docs" / "governance" / "stage_registry.v1.json"
REGISTRY_VALIDATOR_PATH = REPO / "scripts" / "governance" / "validate_stage_registry.py"
REQUIRED_MAPPING_FIELDS = [
    "checklist_item_id",
    "registry_id",
    "item_id",
    "item_title",
    "stage_id",
    "layer",
    "owner_plane",
    "parent_id",
    "next_action_ref",
    "blocked_by_ref",
]
FORBIDDEN_SCHEMA_KEYS = {
    "required_fields",
    "field_semantics",
    "allowed_layers",
    "allowed_status_semantics",
    "allowed_owner_planes",
    "allowed_evidence_types",
    "naming_rules",
}


def _load_registry_validator():
    spec = importlib.util.spec_from_file_location("stage_registry_validator_dep", REGISTRY_VALIDATOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _compile_regex(pattern: str, field_name: str, errors: list[str]) -> re.Pattern[str] | None:
    try:
        return re.compile(pattern)
    except re.error as exc:
        errors.append(f"invalid regex for {field_name}: {exc}")
        return None


def _validate_ref_list(
    entry: dict[str, Any],
    field_name: str,
    known_item_ids: set[str],
    index: int,
    errors: list[str],
) -> None:
    value = entry.get(field_name)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"entries[{index}] {field_name} must be a list of strings")
        return
    unknown = [item for item in value if item not in known_item_ids]
    if unknown:
        errors.append(f"entries[{index}] {field_name} contains unknown refs: {', '.join(unknown)}")


def validate_mapping(
    mapping_payload: dict[str, Any],
    registry_payload: dict[str, Any],
    mapping_path: Path | None = None,
    registry_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []

    registry_validator = _load_registry_validator()
    registry_errors = registry_validator.validate_registry(registry_payload, registry_path or DEFAULT_REGISTRY_PATH)
    if registry_errors:
        errors.append("dependent HONG-21 registry is invalid")
        errors.extend([f"registry::{error}" for error in registry_errors])
        return errors

    if mapping_payload.get("artifact_id") != "stage_registry_mapping.v1":
        errors.append("artifact_id must be 'stage_registry_mapping.v1'")

    if mapping_payload.get("depends_on_registry") != "docs/governance/stage_registry.v1.json":
        errors.append("depends_on_registry must point to docs/governance/stage_registry.v1.json")

    if mapping_payload.get("depends_on_registry_artifact_id") != registry_payload.get("artifact_id"):
        errors.append("depends_on_registry_artifact_id must match stage_registry.v1")

    for key in FORBIDDEN_SCHEMA_KEYS:
        if key in mapping_payload:
            errors.append(f"mapping artifact must not redefine HONG-21 schema key '{key}'")

    required_mapping_fields = mapping_payload.get("mapping_required_fields")
    if not isinstance(required_mapping_fields, list):
        errors.append("mapping_required_fields must be a list")
        required_mapping_fields = []
    elif set(required_mapping_fields) != set(REQUIRED_MAPPING_FIELDS):
        errors.append("mapping_required_fields must match the HONG-22 required field set exactly")

    mapping_rule_dictionary = mapping_payload.get("mapping_rule_dictionary")
    if not isinstance(mapping_rule_dictionary, dict):
        errors.append("mapping_rule_dictionary must be an object")
        mapping_rule_dictionary = {}

    for field_name in REQUIRED_MAPPING_FIELDS:
        if field_name not in mapping_rule_dictionary:
            errors.append(f"mapping_rule_dictionary missing '{field_name}'")

    entries = mapping_payload.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("entries must be a non-empty list")
        return errors

    allowed_layers = set(registry_payload.get("allowed_layers") or [])
    allowed_owner_planes = set(registry_payload.get("allowed_owner_planes") or [])
    naming_rules = registry_payload.get("naming_rules") or {}
    stage_pattern = _compile_regex(str(naming_rules.get("stage_id_pattern", "")), "stage_id_pattern", errors)
    registry_pattern = _compile_regex(str(naming_rules.get("registry_id_pattern", "")), "registry_id_pattern", errors)
    item_pattern = _compile_regex(str(naming_rules.get("item_id_pattern", "")), "item_id_pattern", errors)

    checklist_ids: list[str] = []
    registry_ids: list[str] = []
    item_ids: list[str] = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{index}] must be an object")
            continue

        for field_name in REQUIRED_MAPPING_FIELDS:
            if field_name not in entry:
                errors.append(f"entries[{index}] missing '{field_name}'")

        for field_name in ["checklist_item_id", "registry_id", "item_id", "item_title", "stage_id", "layer", "owner_plane"]:
            value = entry.get(field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"entries[{index}] '{field_name}' must be a non-empty string")

        checklist_item_id = entry.get("checklist_item_id")
        registry_id = entry.get("registry_id")
        item_id = entry.get("item_id")
        stage_id = entry.get("stage_id")

        if isinstance(checklist_item_id, str):
            checklist_ids.append(checklist_item_id)
        if isinstance(registry_id, str):
            registry_ids.append(registry_id)
        if isinstance(item_id, str):
            item_ids.append(item_id)

        if entry.get("layer") not in allowed_layers:
            errors.append(f"entries[{index}] has invalid layer '{entry.get('layer')}'")

        if entry.get("owner_plane") not in allowed_owner_planes:
            errors.append(f"entries[{index}] has invalid owner_plane '{entry.get('owner_plane')}'")

        if stage_pattern and isinstance(stage_id, str) and not stage_pattern.fullmatch(stage_id):
            errors.append(f"entries[{index}] stage_id does not match stage_id_pattern")

        for field_name, pattern in [
            ("checklist_item_id", item_pattern),
            ("registry_id", registry_pattern),
            ("item_id", item_pattern),
        ]:
            value = entry.get(field_name)
            if pattern and isinstance(value, str) and not pattern.fullmatch(value):
                errors.append(f"entries[{index}] {field_name} does not match HONG-21 naming rules")
            if isinstance(value, str) and isinstance(stage_id, str) and not value.startswith(f"{stage_id}-"):
                errors.append(f"entries[{index}] {field_name} must use the '{stage_id}-' stage prefix")

        parent_id = entry.get("parent_id")
        if parent_id is not None and not isinstance(parent_id, str):
            errors.append(f"entries[{index}] parent_id must be a string or null")
        elif isinstance(parent_id, str):
            if item_pattern and not item_pattern.fullmatch(parent_id):
                errors.append(f"entries[{index}] parent_id does not match HONG-21 naming rules")
            if isinstance(stage_id, str) and not parent_id.startswith(f"{stage_id}-"):
                errors.append(f"entries[{index}] parent_id must use the '{stage_id}-' stage prefix")
            if parent_id == item_id:
                errors.append(f"entries[{index}] parent_id cannot equal item_id")

        next_action_ref = entry.get("next_action_ref")
        if next_action_ref is not None and not isinstance(next_action_ref, str):
            errors.append(f"entries[{index}] next_action_ref must be a string or null")

        blocked_by_ref = entry.get("blocked_by_ref")
        if not isinstance(blocked_by_ref, list) or any(not isinstance(item, str) for item in blocked_by_ref):
            errors.append(f"entries[{index}] blocked_by_ref must be a list of strings")

    def _duplicates(values: list[str]) -> list[str]:
        seen: set[str] = set()
        dupes: set[str] = set()
        for value in values:
            if value in seen:
                dupes.add(value)
            seen.add(value)
        return sorted(dupes)

    for label, values in [
        ("checklist_item_id", checklist_ids),
        ("registry_id", registry_ids),
        ("item_id", item_ids),
    ]:
        dupes = _duplicates(values)
        if dupes:
            errors.append(f"duplicate {label}: {', '.join(dupes)}")

    known_item_ids = set(item_ids)
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue

        parent_id = entry.get("parent_id")
        if isinstance(parent_id, str) and parent_id not in known_item_ids:
            errors.append(f"entries[{index}] parent_id references unknown item_id '{parent_id}'")

        next_action_ref = entry.get("next_action_ref")
        if isinstance(next_action_ref, str) and next_action_ref not in known_item_ids:
            errors.append(f"entries[{index}] next_action_ref references unknown item_id '{next_action_ref}'")

        _validate_ref_list(entry, "blocked_by_ref", known_item_ids, index, errors)

    return errors


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    mapping_path = Path(argv[0]).resolve() if argv else DEFAULT_MAPPING_PATH
    registry_path = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_REGISTRY_PATH

    mapping_payload = load_json(mapping_path)
    registry_payload = load_json(registry_path)
    errors = validate_mapping(mapping_payload, registry_payload, mapping_path, registry_path)
    if errors:
        print("FAIL: stage registry mapping validation failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"PASS: stage registry mapping validation ok ({mapping_path.relative_to(REPO).as_posix()})")
    print(f"PASS: validated {len(mapping_payload['entries'])} mapping entr{'y' if len(mapping_payload['entries']) == 1 else 'ies'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
