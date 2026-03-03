#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

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


def format_duration_human(total_seconds: int) -> str:
    seconds = max(0, int(total_seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if days or hours:
        parts.append(f"{hours}h")
    if days or hours or minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _select_latest_open_pr(open_pr_rows: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    rows = [row for row in open_pr_rows if isinstance(row, dict)]
    if not rows:
        return None

    def _number(row: dict[str, Any]) -> int:
        try:
            return int(row.get("number", 0) or 0)
        except (TypeError, ValueError):
            return 0

    return sorted(rows, key=_number, reverse=True)[0]


def render_cooldown_message(kind: str, remaining_seconds: int, open_pr_rows: Iterable[dict[str, Any]]) -> str:
    remaining_human = format_duration_human(remaining_seconds)
    lines = [
        f"[auto_pr] Skip due to cooldown/dedupe: kind={kind} remaining={remaining_human} ({int(remaining_seconds)}s)"
    ]
    latest = _select_latest_open_pr(open_pr_rows)
    if latest and str(latest.get("url", "")).strip():
        number = latest.get("number")
        title = str(latest.get("title", "")).strip()
        head_ref = str(latest.get("headRefName", "")).strip()
        lines.append(f"[auto_pr] Open PR for class '{kind}': {latest['url']}")
        lines.append(f"[auto_pr] Latest open PR details: #{number} | {title} | {head_ref}")
    else:
        lines.append("[auto_pr] No open PR found; rerun after cooldown or use --cooldown-hours 0 (if operator chooses).")
    return "\n".join(lines)


def render_pr_body(title: str, paths: Iterable[str], preflight_transcript: str) -> str:
    changed = normalize_paths(paths)
    lines: list[str] = [
        "## Summary",
        str(title).strip(),
        "",
        "## Changed Paths",
    ]
    if changed:
        lines.extend(f"- `{path}`" for path in changed)
    else:
        lines.append("- (none)")
    lines.extend(
        [
            "",
            "## Safety Statement",
            "- Allowlist guard enforced (`docs/**`, `_local/**`, `research/**`, `scripts/**`).",
            "- `src/hongstr/**` is blocked.",
            "- `data/**` artifacts are not committed.",
            "- `report_only` workflow is preserved.",
            "",
            "## Rollback",
            "```bash",
            "git revert <merge_commit_sha>",
            "```",
            "",
            "## Preflight Transcript",
            "```bash",
            str(preflight_transcript).rstrip("\n"),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


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


def cmd_render_pr_body(args: argparse.Namespace) -> int:
    if args.paths:
        paths = normalize_paths(args.paths)
    elif args.paths_file:
        paths = normalize_paths(Path(args.paths_file).read_text(encoding="utf-8").splitlines())
    else:
        paths = read_paths_from_stdin()

    preflight = args.preflight_text
    if args.preflight_file:
        preflight = Path(args.preflight_file).read_text(encoding="utf-8")

    print(render_pr_body(args.title, paths, preflight), end="")
    return 0


def cmd_render_cooldown_message(args: argparse.Namespace) -> int:
    try:
        payload = json.loads(args.open_pr_json or "[]")
    except json.JSONDecodeError:
        payload = []
    if not isinstance(payload, list):
        payload = []
    print(render_cooldown_message(args.kind, int(args.remaining_s), payload), end="")
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

    p_render = sub.add_parser("render-pr-body", help="Render PR markdown body safely from title/paths/preflight")
    p_render.add_argument("--title", required=True)
    p_render.add_argument("--paths-file", default="")
    p_render.add_argument("--preflight-file", default="")
    p_render.add_argument("--preflight-text", default="")
    p_render.add_argument("paths", nargs="*")
    p_render.set_defaults(func=cmd_render_pr_body)

    p_cooldown = sub.add_parser(
        "render-cooldown-message",
        help="Render cooldown/dedupe message with operator-friendly hint and optional open PR details",
    )
    p_cooldown.add_argument("--kind", required=True)
    p_cooldown.add_argument("--remaining-s", type=int, required=True)
    p_cooldown.add_argument("--open-pr-json", default="[]")
    p_cooldown.set_defaults(func=cmd_render_cooldown_message)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
