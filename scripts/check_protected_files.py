#!/usr/bin/env python3
"""Fail when protected files are staged for commit unless explicitly overridden."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(out.strip())


def _git_paths(staged: bool) -> set[str]:
    cmd = ["git", "diff", "--name-only"]
    if staged:
        cmd.insert(2, "--cached")
    out = subprocess.check_output(cmd, text=True)
    return {line.strip() for line in out.splitlines() if line.strip()}


def _load_protected(path: Path) -> set[str]:
    items: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        items.add(line)
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protected-list",
        default="configs/protected_files.txt",
        help="relative path of protected files list",
    )
    parser.add_argument(
        "--scope",
        choices=("staged", "working", "all"),
        default="staged",
        help="diff scope: staged only, working tree only, or both",
    )
    args = parser.parse_args()

    if os.getenv("ALLOW_PROTECTED_TOUCH") == "1":
        print("ALLOW_PROTECTED_TOUCH=1 set; skipping protected files check.")
        return 0

    root = _repo_root()
    protected = _load_protected(root / args.protected_list)
    if not protected:
        print("No protected files configured.")
        return 0

    changed: set[str] = set()
    if args.scope in {"staged", "all"}:
        changed |= _git_paths(staged=True)
    if args.scope in {"working", "all"}:
        changed |= _git_paths(staged=False)

    touched = sorted(changed & protected)
    if not touched:
        print("Protected files check passed.")
        return 0

    print("Blocked: protected files touched:")
    for path in touched:
        print(f" - {path}")
    print("If intentional, rerun with ALLOW_PROTECTED_TOUCH=1.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
