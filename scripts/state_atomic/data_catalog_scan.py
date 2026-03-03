#!/usr/bin/env python3
"""
Scan producer manifests and build deterministic catalog/change payloads.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UTC = timezone.utc
DEFAULT_MANIFEST_DIR = Path("reports/state_atomic/manifests")
DEFAULT_SCAN_PATH = Path("reports/state_atomic/data_catalog_scan.json")
COMPARISON_FIELDS = (
    "schema_version",
    "producer",
    "cadence",
    "path_patterns",
    "symbols",
    "metrics",
    "periods",
    "sources",
    "notes",
)


def now_utc_iso() -> str:
    return (
        datetime.now(tz=UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _sorted_unique_strs(values: Any, field_name: str) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list")
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} items must be non-empty strings")
        out.append(value.strip())
    return sorted(dict.fromkeys(out))


def normalize_manifest(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("manifest must be an object")

    dataset_id = str(payload.get("dataset_id") or "").strip()
    schema_version = str(payload.get("schema_version") or "").strip()
    producer = str(payload.get("producer") or "").strip()
    cadence = str(payload.get("cadence") or "").strip()
    notes = str(payload.get("notes") or "")
    if not dataset_id:
        raise ValueError("dataset_id must be a non-empty string")
    if not schema_version:
        raise ValueError("schema_version must be a non-empty string")
    if not producer:
        raise ValueError("producer must be a non-empty string")
    if not cadence:
        raise ValueError("cadence must be a non-empty string")

    path_patterns = payload.get("path_patterns")
    if not isinstance(path_patterns, dict):
        raise ValueError("path_patterns must be an object")
    root = str(path_patterns.get("root") or "").strip()
    template = str(path_patterns.get("template") or "").strip()
    if not root or not template:
        raise ValueError("path_patterns.root/template must be non-empty strings")

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")
    generated_utc = str(provenance.get("generated_utc") or "").strip()
    code_ref = str(provenance.get("code_ref") or "").strip() or "unknown"
    if not generated_utc:
        raise ValueError("provenance.generated_utc must be a non-empty string")

    sources_raw = payload.get("sources")
    if not isinstance(sources_raw, list):
        raise ValueError("sources must be a list")
    sources: list[dict[str, Any]] = []
    for source in sources_raw:
        if not isinstance(source, dict):
            raise ValueError("sources items must be objects")
        name = str(source.get("name") or "").strip()
        if not name:
            raise ValueError("sources.name must be a non-empty string")
        endpoints = _sorted_unique_strs(source.get("endpoints"), "sources.endpoints")
        sources.append({"name": name, "endpoints": endpoints})
    sources = sorted(sources, key=lambda row: row["name"])

    return {
        "dataset_id": dataset_id,
        "schema_version": schema_version,
        "producer": producer,
        "cadence": cadence,
        "path_patterns": {"root": root, "template": template},
        "symbols": _sorted_unique_strs(payload.get("symbols"), "symbols"),
        "metrics": _sorted_unique_strs(payload.get("metrics"), "metrics"),
        "periods": _sorted_unique_strs(payload.get("periods"), "periods"),
        "sources": sources,
        "provenance": {"generated_utc": generated_utc, "code_ref": code_ref},
        "notes": notes,
    }


def scan_manifest_dir(manifest_dir: Path) -> dict[str, Any]:
    warnings: list[str] = []
    skipped_dataset_ids: list[str] = []
    datasets: list[dict[str, Any]] = []
    if manifest_dir.exists():
        for path in sorted(manifest_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                datasets.append(normalize_manifest(payload))
            except Exception as exc:
                skipped_dataset_ids.append(path.stem)
                warnings.append(f"skipped {path.as_posix()}: {exc}")

    datasets = sorted(datasets, key=lambda row: row["dataset_id"])
    return {
        "ts_utc": now_utc_iso(),
        "datasets": datasets,
        "warnings": warnings,
        "skipped_dataset_ids": sorted(dict.fromkeys(skipped_dataset_ids)),
    }


def build_catalog_payload(scan_payload: Any, *, ts_utc: str | None = None) -> dict[str, Any]:
    datasets: list[dict[str, Any]] = []
    if isinstance(scan_payload, dict):
        raw = scan_payload.get("datasets")
        if isinstance(raw, list):
            for item in raw:
                try:
                    datasets.append(normalize_manifest(item))
                except Exception:
                    continue
    return {
        "ts_utc": ts_utc or now_utc_iso(),
        "datasets": sorted(datasets, key=lambda row: row["dataset_id"]),
    }


def _comparable_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {field: manifest.get(field) for field in COMPARISON_FIELDS}


def _fields_changed(prev_row: dict[str, Any], current_row: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for field in COMPARISON_FIELDS:
        if field == "path_patterns":
            prev_path = prev_row.get("path_patterns") if isinstance(prev_row.get("path_patterns"), dict) else {}
            curr_path = current_row.get("path_patterns") if isinstance(current_row.get("path_patterns"), dict) else {}
            if prev_path.get("root") != curr_path.get("root"):
                changed.append("path_patterns.root")
            if prev_path.get("template") != curr_path.get("template"):
                changed.append("path_patterns.template")
            continue
        if prev_row.get(field) != current_row.get(field):
            changed.append(field)
    return changed


def _dataset_summary(row: dict[str, Any]) -> str:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), list) else []
    symbols = row.get("symbols") if isinstance(row.get("symbols"), list) else []
    periods = row.get("periods") if isinstance(row.get("periods"), list) else []
    return (
        f"{len(metrics)} metrics, {len(symbols)} symbols, "
        f"{','.join(periods) if periods else 'no periods'}"
    )


def build_catalog_changes(
    prev_catalog: Any,
    current_catalog: dict[str, Any],
    *,
    ts_utc: str | None = None,
    ignored_removed_dataset_ids: list[str] | None = None,
) -> dict[str, Any]:
    prev_rows = []
    prev_ts_utc = None
    if isinstance(prev_catalog, dict):
        prev_ts = prev_catalog.get("ts_utc")
        if isinstance(prev_ts, str) and prev_ts.strip():
            prev_ts_utc = prev_ts
        raw_prev = prev_catalog.get("datasets")
        if isinstance(raw_prev, list):
            for item in raw_prev:
                try:
                    prev_rows.append(normalize_manifest(item))
                except Exception:
                    continue

    current_rows = []
    raw_current = current_catalog.get("datasets")
    if isinstance(raw_current, list):
        for item in raw_current:
            try:
                current_rows.append(normalize_manifest(item))
            except Exception:
                continue

    prev_map = {row["dataset_id"]: row for row in prev_rows}
    current_map = {row["dataset_id"]: row for row in current_rows}
    ignored_removed = set(ignored_removed_dataset_ids or [])

    added = [
        {
            "dataset_id": dataset_id,
            "summary": (
                f"{'initial dataset' if prev_ts_utc is None else 'dataset added'}: "
                f"{_dataset_summary(current_map[dataset_id])}"
            ),
        }
        for dataset_id in sorted(set(current_map) - set(prev_map))
    ]
    removed = [
        {
            "dataset_id": dataset_id,
            "summary": f"dataset removed: {_dataset_summary(prev_map[dataset_id])}",
        }
        for dataset_id in sorted((set(prev_map) - set(current_map)) - ignored_removed)
    ]

    updated: list[dict[str, Any]] = []
    for dataset_id in sorted(set(prev_map) & set(current_map)):
        changed = _fields_changed(
            _comparable_manifest(prev_map[dataset_id]),
            _comparable_manifest(current_map[dataset_id]),
        )
        if not changed:
            continue
        updated.append(
            {
                "dataset_id": dataset_id,
                "fields_changed": changed,
                "summary": "updated fields: " + ", ".join(changed),
            }
        )

    return {
        "ts_utc": ts_utc or now_utc_iso(),
        "prev_ts_utc": prev_ts_utc,
        "added_datasets": added,
        "removed_datasets": removed,
        "updated_datasets": updated,
    }


def build_changes_summary(changes_payload: Any) -> tuple[str, str]:
    if not isinstance(changes_payload, dict):
        return "UNKNOWN", "Dataset changes: UNKNOWN"
    added = changes_payload.get("added_datasets")
    removed = changes_payload.get("removed_datasets")
    updated = changes_payload.get("updated_datasets")
    if not isinstance(added, list) or not isinstance(removed, list) or not isinstance(updated, list):
        return "UNKNOWN", "Dataset changes: UNKNOWN"
    summary = f"Dataset changes: +{len(added)}, ~{len(updated)}, -{len(removed)}"
    if changes_payload.get("prev_ts_utc") is None:
        summary = "Dataset changes: initial " + summary.replace("Dataset changes: ", "")
    return "OK", summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan producer manifests for the data catalog.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--output", default=str(DEFAULT_SCAN_PATH))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_dir = Path(args.manifest_dir)
    output = Path(args.output)
    payload = scan_manifest_dir(manifest_dir)
    write_atomic_json(output, payload)
    print(f"manifest_dir={manifest_dir}")
    print(f"datasets={len(payload.get('datasets', []))}")
    print(f"warnings={len(payload.get('warnings', []))}")
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
