#!/usr/bin/env python3
"""
Read-only helpers for SSOT discovery/report scripts.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


def read_json_file(path: Path) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def repo_relative_path(path: Path, repo_root: Path) -> str:
    target = path.resolve()
    try:
        return target.relative_to(repo_root.resolve()).as_posix()
    except Exception:
        return target.as_posix()


def parse_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_utc_iso(value: Any) -> str | None:
    parsed = parse_utc(value)
    if parsed is None:
        return None
    return parsed.isoformat().replace("+00:00", "Z")


def iter_nested_mappings(node: Any, max_depth: int = 4) -> Iterator[dict[str, Any]]:
    stack: list[tuple[Any, int]] = [(node, 0)]
    seen: set[int] = set()

    while stack:
        current, depth = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))

        if isinstance(current, dict):
            yield current
            if depth >= max_depth:
                continue
            for value in current.values():
                if isinstance(value, (dict, list)):
                    stack.append((value, depth + 1))
            continue

        if isinstance(current, list) and depth < max_depth:
            for item in current:
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))
