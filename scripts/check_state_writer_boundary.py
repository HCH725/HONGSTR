#!/usr/bin/env python3
"""
Guardrail: canonical data/state snapshots must be written only by state_snapshots.py.

This script enforces three machine-checkable conditions:
1. The writer inventory covers every canonical data/state artifact emitted by state_snapshots.py.
2. Every inventory entry points to the single designated writer and orchestrator.
3. No non-test path under scripts/_local/web writes an inventoried canonical artifact.
"""
from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

from state_writer_inventory import (
    ALLOWED_OWNER_PLANES,
    CANONICAL_STATE_WRITER_INVENTORY,
    DESIGNATED_ORCHESTRATOR,
    DESIGNATED_WRITER,
    inventory_filenames,
    inventory_paths,
)

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_CANONICAL_WRITER = Path(DESIGNATED_WRITER)
SCAN_ROOTS = (Path("scripts"), Path("_local"), Path("web"))
SCAN_SUFFIXES = {".py", ".sh", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
SKIP_DIR_NAMES = {".next", "node_modules", ".venv", "__pycache__", ".git"}
CANONICAL_FILES = set(inventory_filenames())
STATE_WRITER_SCRIPT = ROOT / ALLOWED_CANONICAL_WRITER

WRITE_HINT_RE = re.compile(
    r"(write_text\(|write_json\(|write_jsonl\(|json\.dump\(|open\([^)]*,\s*[\"']w[\"'])"
)


def _is_test_or_doc(path: Path) -> bool:
    rel = path.as_posix()
    name = path.name
    if "/tests/" in rel or rel.endswith("/test_local_smoke.py"):
        return True
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    return False


def _expr_to_path(node: ast.AST, env: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Path"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _expr_to_path(node.left, env)
        right = _expr_to_path(node.right, env)
        if left is None or right is None:
            return None
        return str(Path(left) / right).replace("\\", "/")
    return None


def _state_snapshots_written_paths() -> set[str]:
    tree = ast.parse(STATE_WRITER_SCRIPT.read_text(encoding="utf-8"))
    env: dict[str, str] = {}
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = _expr_to_path(stmt.value, env)
        if value is not None:
            env[target.id] = value

    written_paths: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Name) or node.func.id not in {"write_json", "write_jsonl"}:
            continue
        path = _expr_to_path(node.args[0], env)
        if path and path.startswith("data/state/"):
            written_paths.add(path)
    return written_paths


def inventory_shape_issues() -> list[str]:
    issues: list[str] = []
    required_fields = {
        "artifact_id",
        "canonical_path",
        "designated_writer",
        "designated_orchestrator",
        "owner_plane",
        "owner_role",
        "publication_tier",
        "status",
        "update_cadence",
        "responsibility",
        "degrade_hint",
        "kill_hint",
        "sop_hint",
    }
    seen_paths: set[str] = set()
    for entry in CANONICAL_STATE_WRITER_INVENTORY:
        artifact_id = str(entry.get("artifact_id") or "<missing-artifact-id>")
        missing = sorted(field for field in required_fields if not str(entry.get(field) or "").strip())
        if missing:
            issues.append(f"{artifact_id}: missing required fields: {', '.join(missing)}")
        path = str(entry.get("canonical_path") or "").strip()
        if path in seen_paths:
            issues.append(f"{artifact_id}: duplicate canonical_path {path}")
        if path:
            seen_paths.add(path)
        if entry.get("designated_writer") != DESIGNATED_WRITER:
            issues.append(f"{artifact_id}: designated_writer must be {DESIGNATED_WRITER}")
        if entry.get("designated_orchestrator") != DESIGNATED_ORCHESTRATOR:
            issues.append(f"{artifact_id}: designated_orchestrator must be {DESIGNATED_ORCHESTRATOR}")
        if entry.get("owner_plane") not in ALLOWED_OWNER_PLANES:
            issues.append(
                f"{artifact_id}: owner_plane must be one of {', '.join(ALLOWED_OWNER_PLANES)}"
            )
    return issues


def inventory_coverage_issues() -> tuple[list[str], list[str]]:
    writer_paths = _state_snapshots_written_paths()
    inventory = set(inventory_paths())
    missing = sorted(writer_paths - inventory)
    extra = sorted(inventory - writer_paths)
    return missing, extra


def scan() -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    for scan_root in SCAN_ROOTS:
        base = ROOT / scan_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            rel = path.relative_to(ROOT)
            if _is_test_or_doc(rel):
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for idx, line in enumerate(lines, start=1):
                if not WRITE_HINT_RE.search(line):
                    continue
                if not any(name in line for name in CANONICAL_FILES):
                    continue
                if rel == ALLOWED_CANONICAL_WRITER:
                    continue
                violations.append((rel, idx, line.strip()))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check canonical data/state writer boundary.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when violations are found.")
    args = parser.parse_args()

    shape_issues = inventory_shape_issues()
    missing, extra = inventory_coverage_issues()
    violations = scan()

    if not shape_issues and not missing and not extra and not violations:
        print(
            "OK: canonical data/state writer boundary holds "
            f"({DESIGNATED_WRITER} only; inventory covers {len(inventory_paths())} artifacts)."
        )
        return 0

    print("FAIL: canonical data/state writer boundary check failed.")
    if shape_issues:
        print("Inventory shape issues:")
        for issue in shape_issues:
            print(f" - {issue}")
    if missing:
        print("Writer inventory missing canonical outputs emitted by state_snapshots.py:")
        for path in missing:
            print(f" - {path}")
    if extra:
        print("Writer inventory contains stale paths not emitted by state_snapshots.py:")
        for path in extra:
            print(f" - {path}")
    if violations:
        print("Detected non-canonical writers for inventoried data/state snapshot filenames:")
        for rel, lineno, line in violations:
            print(f" - {rel}:{lineno}: {line}")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
