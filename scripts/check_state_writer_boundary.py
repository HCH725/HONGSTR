#!/usr/bin/env python3
"""
Guardrail: canonical data/state snapshots must be written only by state_snapshots.py.

This script is intentionally static/lightweight:
- scans scripts/_local/web source files
- looks for canonical snapshot filenames on lines that also look like write operations
- fails when writer is outside scripts/state_snapshots.py
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_CANONICAL_WRITER = Path("scripts/state_snapshots.py")
SCAN_ROOTS = (Path("scripts"), Path("_local"), Path("web"))
SCAN_SUFFIXES = {".py", ".sh", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
SKIP_DIR_NAMES = {".next", "node_modules", ".venv", "__pycache__", ".git"}
CANONICAL_FILES = {
    "coverage_table.jsonl",
    "coverage_latest.json",
    "coverage_summary.json",
    "strategy_pool_summary.json",
    "regime_monitor_latest.json",
    "regime_monitor_summary.json",
    "freshness_table.json",
    "execution_mode.json",
    "services_heartbeat.json",
    "coverage_matrix_latest.json",
    "brake_health_latest.json",
    "system_health_latest.json",
}

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

    violations = scan()
    if not violations:
        print("OK: canonical data/state writer boundary holds (scripts/state_snapshots.py only).")
        return 0

    print("FAIL: detected non-canonical writers for data/state snapshot filenames:")
    for rel, lineno, line in violations:
        print(f" - {rel}:{lineno}: {line}")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
