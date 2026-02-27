#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_ALLOW_PREFIXES = ["docs/", "_local/", "research/", "scripts/"]
DEFAULT_BLOCK_PREFIXES = ["src/hongstr/", "data/"]


@dataclass
class Classification:
    kind: str
    title: str


def normalize_paths(paths: Iterable[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        text = str(p).strip()
        if text:
            out.append(text)
    return out


def check_allowlist(
    paths: Iterable[str],
    *,
    allow_prefixes: Iterable[str] | None = None,
    block_prefixes: Iterable[str] | None = None,
) -> tuple[bool, list[str]]:
    allow = list(allow_prefixes or DEFAULT_ALLOW_PREFIXES)
    block = list(block_prefixes or DEFAULT_BLOCK_PREFIXES)

    bad: list[str] = []
    for p in normalize_paths(paths):
        if any(p.startswith(bp) for bp in block):
            bad.append(p)
            continue
        if not any(p.startswith(ap) for ap in allow):
            bad.append(p)
    return len(bad) == 0, bad


def classify_changes(paths: Iterable[str]) -> Classification:
    items = normalize_paths(paths)
    if not items:
        return Classification("no-op", "ops(auto_pr): no changes")

    sets = {
        "docs": all(p.startswith("docs/") for p in items),
        "docs_skills": all(p.startswith("docs/skills/") for p in items),
        "local": all(p.startswith("_local/") for p in items),
        "research": all(p.startswith("research/") for p in items),
        "scripts": all(p.startswith("scripts/") for p in items),
    }

    if sets["docs_skills"]:
        return Classification("skills-docs", "docs(skills): refresh skills docs")
    if sets["docs"]:
        return Classification("docs-only", "docs(auto_pr): refresh docs")
    if sets["research"]:
        return Classification("research-only", "research(auto_pr): report-only research updates")
    if sets["local"]:
        return Classification("local-only", "ops(_local): control-plane docs/tests")
    if sets["scripts"]:
        return Classification("scripts-only", "ops(auto_pr): script-only maintenance")

    has_docs = any(p.startswith("docs/") for p in items)
    has_research = any(p.startswith("research/") for p in items)
    has_scripts = any(p.startswith("scripts/") for p in items)
    has_local = any(p.startswith("_local/") for p in items)

    if has_docs and has_research and not has_scripts and not has_local:
        return Classification("research-docs", "research/docs: report-only governance refresh")

    return Classification("mixed-allowlist", "ops(auto_pr): allowlisted mixed update")


def read_paths_from_stdin() -> list[str]:
    return normalize_paths(sys.stdin.read().splitlines())


def cmd_check(args: argparse.Namespace) -> int:
    paths = args.paths or read_paths_from_stdin()
    ok, bad = check_allowlist(paths, allow_prefixes=args.allow_prefix, block_prefixes=args.block_prefix)
    payload = {
        "ok": ok,
        "paths": normalize_paths(paths),
        "bad_paths": bad,
        "allow_prefixes": list(args.allow_prefix),
        "block_prefixes": list(args.block_prefix),
    }
    print(json.dumps(payload, indent=2))
    return 0 if ok else 2


def cmd_classify(args: argparse.Namespace) -> int:
    paths = args.paths or read_paths_from_stdin()
    cls = classify_changes(paths)
    payload = {
        "kind": cls.kind,
        "title": cls.title,
        "paths": normalize_paths(paths),
    }
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Auto-PR allowlist and title classification helpers")
    sub = p.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Validate changed paths against allow/block prefix lists")
    p_check.add_argument("paths", nargs="*")
    p_check.add_argument("--allow-prefix", action="append", default=list(DEFAULT_ALLOW_PREFIXES))
    p_check.add_argument("--block-prefix", action="append", default=list(DEFAULT_BLOCK_PREFIXES))
    p_check.set_defaults(func=cmd_check)

    p_class = sub.add_parser("classify", help="Classify change set for PR title selection")
    p_class.add_argument("paths", nargs="*")
    p_class.set_defaults(func=cmd_classify)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
