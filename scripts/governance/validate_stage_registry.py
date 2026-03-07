#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = REPO / "docs" / "governance" / "stage_registry.v1.json"
MANDATORY_FIELDS = [
    "stage_id",
    "stage_name",
    "registry_id",
    "item_id",
    "item_title",
    "layer",
    "owner_plane",
    "status_semantics",
    "evidence_type",
    "evidence_ref",
    "degrade_rule",
    "kill_switch",
    "blocked_by",
    "next_action",
]
ALLOWED_LAYERS = {"Layer1", "Layer2", "Layer3", "Layer4"}
ALLOWED_STATUS_VOCAB = {"TODO", "IN_PROGRESS", "BLOCKED", "DONE"}


def load_registry(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_compiled_regex(pattern: str, field_name: str, errors: list[str]) -> re.Pattern[str] | None:
    try:
        return re.compile(pattern)
    except re.error as exc:
        errors.append(f"invalid regex for {field_name}: {exc}")
        return None


def validate_registry(payload: dict[str, Any], source_path: Path | None = None) -> list[str]:
    errors: list[str] = []

    if payload.get("artifact_id") != "stage_registry.v1":
        errors.append("artifact_id must be 'stage_registry.v1'")

    required_fields = payload.get("required_fields")
    if not isinstance(required_fields, list):
        errors.append("required_fields must be a list")
        required_fields = []

    if set(required_fields) != set(MANDATORY_FIELDS):
        errors.append("required_fields must match the HONG-21 mandatory field set exactly")

    field_semantics = payload.get("field_semantics")
    if not isinstance(field_semantics, dict):
        errors.append("field_semantics must be an object")
        field_semantics = {}

    for field_name in MANDATORY_FIELDS:
        if field_name not in field_semantics:
            errors.append(f"field_semantics missing '{field_name}'")

    allowed_layers = payload.get("allowed_layers")
    if not isinstance(allowed_layers, list):
        errors.append("allowed_layers must be a list")
    elif set(allowed_layers) != ALLOWED_LAYERS:
        errors.append("allowed_layers must be exactly Layer1/Layer2/Layer3/Layer4")

    allowed_statuses = payload.get("allowed_status_semantics")
    if not isinstance(allowed_statuses, list):
        errors.append("allowed_status_semantics must be a list")
    elif set(allowed_statuses) != ALLOWED_STATUS_VOCAB:
        errors.append("allowed_status_semantics must be exactly TODO/IN_PROGRESS/BLOCKED/DONE")

    naming_rules = payload.get("naming_rules")
    if not isinstance(naming_rules, dict):
        errors.append("naming_rules must be an object")
        naming_rules = {}

    stage_pattern = _ensure_compiled_regex(str(naming_rules.get("stage_id_pattern", "")), "stage_id_pattern", errors)
    registry_pattern = _ensure_compiled_regex(str(naming_rules.get("registry_id_pattern", "")), "registry_id_pattern", errors)
    item_pattern = _ensure_compiled_regex(str(naming_rules.get("item_id_pattern", "")), "item_id_pattern", errors)

    entries = payload.get("baseline_entries")
    if not isinstance(entries, list) or not entries:
        errors.append("baseline_entries must be a non-empty list")
        entries = []

    allowed_owner_planes = payload.get("allowed_owner_planes")
    if not isinstance(allowed_owner_planes, list) or not allowed_owner_planes:
        errors.append("allowed_owner_planes must be a non-empty list")
        allowed_owner_planes = []

    allowed_evidence_types = payload.get("allowed_evidence_types")
    if not isinstance(allowed_evidence_types, list) or not allowed_evidence_types:
        errors.append("allowed_evidence_types must be a non-empty list")
        allowed_evidence_types = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"baseline_entries[{index}] must be an object")
            continue

        for field_name in MANDATORY_FIELDS:
            if field_name not in entry:
                errors.append(f"baseline_entries[{index}] missing '{field_name}'")

        if entry.get("layer") not in ALLOWED_LAYERS:
            errors.append(f"baseline_entries[{index}] has invalid layer '{entry.get('layer')}'")

        if entry.get("status_semantics") not in ALLOWED_STATUS_VOCAB:
            errors.append(
                f"baseline_entries[{index}] has invalid status_semantics '{entry.get('status_semantics')}'"
            )

        if entry.get("owner_plane") not in allowed_owner_planes:
            errors.append(f"baseline_entries[{index}] has invalid owner_plane '{entry.get('owner_plane')}'")

        if entry.get("evidence_type") not in allowed_evidence_types:
            errors.append(f"baseline_entries[{index}] has invalid evidence_type '{entry.get('evidence_type')}'")

        blocked_by = entry.get("blocked_by")
        if not isinstance(blocked_by, list) or any(not isinstance(item, str) for item in blocked_by):
            errors.append(f"baseline_entries[{index}] blocked_by must be a list of strings")

        for field_name in ["stage_id", "stage_name", "registry_id", "item_id", "item_title", "evidence_ref", "next_action"]:
            value = entry.get(field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"baseline_entries[{index}] '{field_name}' must be a non-empty string")

        for field_name in ["degrade_rule", "kill_switch"]:
            value = entry.get(field_name)
            if not isinstance(value, str) or len(value.strip()) < 10:
                errors.append(f"baseline_entries[{index}] '{field_name}' must be a meaningful string")

        if stage_pattern and isinstance(entry.get("stage_id"), str) and not stage_pattern.fullmatch(entry["stage_id"]):
            errors.append(f"baseline_entries[{index}] stage_id does not match stage_id_pattern")

        if registry_pattern and isinstance(entry.get("registry_id"), str) and not registry_pattern.fullmatch(entry["registry_id"]):
            errors.append(f"baseline_entries[{index}] registry_id does not match registry_id_pattern")

        if item_pattern and isinstance(entry.get("item_id"), str) and not item_pattern.fullmatch(entry["item_id"]):
            errors.append(f"baseline_entries[{index}] item_id does not match item_id_pattern")

    if source_path is not None:
        expected_ref = source_path.relative_to(REPO).as_posix()
        for index, entry in enumerate(entries):
            if isinstance(entry, dict) and entry.get("evidence_type") == "repo_path":
                if entry.get("evidence_ref") != expected_ref:
                    errors.append(
                        f"baseline_entries[{index}] repo_path evidence_ref must equal '{expected_ref}'"
                    )

    return errors


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    registry_path = Path(argv[0]).resolve() if argv else DEFAULT_REGISTRY_PATH
    payload = load_registry(registry_path)
    errors = validate_registry(payload, registry_path)
    if errors:
        print("FAIL: stage registry validation failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"PASS: stage registry validation ok ({registry_path.relative_to(REPO).as_posix()})")
    print(f"PASS: validated {len(payload['baseline_entries'])} baseline entr{'y' if len(payload['baseline_entries']) == 1 else 'ies'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
