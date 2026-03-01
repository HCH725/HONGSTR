#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def _normalize_pattern(pattern: str) -> str:
    return str(pattern or "").strip().strip("`").replace("\\", "/")


def _is_allowed(path: str, pattern: str) -> bool:
    norm_path = str(path or "").strip().strip("/")
    norm_pattern = _normalize_pattern(pattern)
    if not norm_path or not norm_pattern:
        return False
    if norm_pattern.endswith("/**"):
        base = norm_pattern[:-3].rstrip("/")
        return norm_path == base or norm_path.startswith(base + "/")
    if norm_pattern.endswith("/"):
        base = norm_pattern.rstrip("/")
        return norm_path == base or norm_path.startswith(base + "/")
    if any(ch in norm_pattern for ch in "*?["):
        return fnmatch.fnmatch(norm_path, norm_pattern)
    return norm_path == norm_pattern


def _run_git_name_only(args: list[str]) -> list[str]:
    output = subprocess.check_output(["git", *args], text=True).strip().splitlines()
    return [line.strip() for line in output if line.strip()]


def _collect_changed_paths() -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    command_sets = [
        ["diff", "--name-only", "--cached"],
        ["diff", "--name-only"],
        ["ls-files", "--others", "--exclude-standard"],
    ]
    for args in command_sets:
        try:
            current_paths = _run_git_name_only(args)
        except subprocess.CalledProcessError:
            continue
        for path in current_paths:
            if path not in seen:
                seen.add(path)
                ordered.append(path)
    if ordered:
        return ordered
    try:
        for path in _run_git_name_only(["diff", "--name-only", "HEAD~1..HEAD"]):
            if path not in seen:
                seen.add(path)
                ordered.append(path)
    except subprocess.CalledProcessError:
        return ordered
    return ordered


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: enforce_allowed_paths.py <ticket_json_path>", file=sys.stderr)
        return 2

    ticket_path = Path(sys.argv[1])
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
    allowed = ticket.get("allowed_paths", [])
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        print("ERROR: allowed_paths must be list[str]", file=sys.stderr)
        return 2

    changed_paths = _collect_changed_paths()
    if not changed_paths:
        print("allowed_paths gate: no changed files detected", file=sys.stderr)
        return 0

    bad = [path for path in changed_paths if not any(_is_allowed(path, pattern) for pattern in allowed)]
    if bad:
        print("ERROR: files changed outside allowed_paths:", file=sys.stderr)
        for item in bad:
            print(item, file=sys.stderr)
        return 3

    print(f"allowed_paths gate: PASS ({len(changed_paths)} files checked)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
