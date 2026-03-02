#!/usr/bin/env python3
"""
scripts/obsidian_changelog_gen.py
----------------------------------
Generate a human-readable ops changelog from git merge history,
optionally enriched with GitHub PR metadata (requires `gh` CLI in PATH).

Usage:
    python scripts/obsidian_changelog_gen.py [--since YYYY-MM-DD] [--dry-run] [--no-gh]

Output:  reports/obsidian_audit/CHANGELOG_ops.md   (NOT committed to git)
Exit:    0 always (report-only; never blocks CI)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = REPO_ROOT / "reports" / "obsidian_audit"

# PR number patterns to pluck from commit messages
_PR_RE = re.compile(r"(?:#|pull/)(\d+)")


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Command {cmd} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _git_merge_log(since: str | None) -> list[dict]:
    """Return list of merge commits with {sha, date, subject}."""
    fmt = "%H\x1f%cs\x1f%s"
    cmd = ["git", "log", "--merges", f"--format={fmt}"]
    if since:
        cmd += [f"--since={since}"]
    raw = _run(cmd)
    entries = []
    for line in raw.splitlines():
        parts = line.split("\x1f", 2)
        if len(parts) == 3:
            sha, date, subject = parts
            entries.append({"sha": sha[:12], "date": date, "subject": subject.strip()})
    return entries


def _extract_pr_number(subject: str) -> str | None:
    m = _PR_RE.search(subject)
    return m.group(1) if m else None


def _gh_pr_metadata(pr_number: str) -> dict | None:
    """Fetch PR metadata from GitHub via gh CLI. Returns None on any failure."""
    try:
        raw = _run(
            ["gh", "pr", "view", pr_number, "--json",
             "number,title,body,labels,mergedAt,headRefName"],
            check=True,
        )
        return json.loads(raw)
    except Exception:
        return None


def _classify_pr(subject: str, labels: list[str]) -> str:
    text = (subject + " ".join(labels)).lower()
    if any(k in text for k in ("feat", "add", "new", "implement")):
        return "feature"
    if any(k in text for k in ("fix", "bug", "patch", "hotfix")):
        return "fix"
    if any(k in text for k in ("refactor", "cleanup", "clean up", "remove", "delete")):
        return "refactor"
    if any(k in text for k in ("test", "spec", "coverage")):
        return "test"
    if any(k in text for k in ("doc", "readme", "runbook", "template")):
        return "docs"
    if any(k in text for k in ("chore", "deps", "bump", "ci", "workflow")):
        return "chore"
    return "other"


def _build_entries(merges: list[dict], use_gh: bool) -> list[dict]:
    entries = []
    for m in merges:
        pr_num = _extract_pr_number(m["subject"])
        meta = None
        if use_gh and pr_num:
            meta = _gh_pr_metadata(pr_num)

        labels = [lbl.get("name", "") for lbl in (meta or {}).get("labels", [])] if meta else []
        kind = _classify_pr(m["subject"], labels)

        entry = {
            "date": m["date"],
            "sha": m["sha"],
            "pr": f"#{pr_num}" if pr_num else "—",
            "kind": kind,
            "title": (meta or {}).get("title") or m["subject"],
            "branch": (meta or {}).get("headRefName", ""),
            "labels": labels,
        }
        entries.append(entry)
    return entries


def _render_changelog(entries: list[dict], since: str | None, now_utc: str) -> str:
    lines = [
        "# HONGSTR Ops Changelog",
        "",
        f"**Generated:** {now_utc}  ",
    ]
    if since:
        lines.append(f"**Since:** {since}  ")
    lines += [
        "**Source:** `git log --merges` (local)  ",
        "**Note:** report-only — not committed to git.",
        "",
    ]

    if not entries:
        lines += ["_No merge commits found for the specified range._", ""]
        return "\n".join(lines)

    # Group by date descending
    by_date: dict[str, list[dict]] = {}
    for e in entries:
        by_date.setdefault(e["date"], []).append(e)

    for date in sorted(by_date.keys(), reverse=True):
        lines.append(f"## {date}")
        lines.append("")
        lines.append("| PR | Kind | Title | SHA | Rollback |")
        lines.append("|----|------|-------|-----|----------|")
        for e in by_date[date]:
            title = e["title"].replace("|", "\\|")[:80]
            rollback = f"`git revert {e['sha']}`"
            lines.append(f"| {e['pr']} | `{e['kind']}` | {title} | `{e['sha']}` | {rollback} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## Rollback Instructions",
        "",
        "To revert a specific merge commit:",
        "```bash",
        "git revert <sha>",
        "git push",
        "gh pr create --title 'revert: <description>' --body 'Rollback for <sha>'",
        "```",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HONGSTR ops changelog generator")
    parser.add_argument("--since", default=None, help="Start date YYYY-MM-DD (default: last 90 days)")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout, do not write file")
    parser.add_argument("--no-gh", action="store_true", help="Skip gh CLI enrichment")
    args = parser.parse_args(argv)

    since = args.since
    if not since:
        from datetime import timedelta
        since = (datetime.now(tz=timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")

    use_gh = not args.no_gh and shutil.which("gh") is not None

    now_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        merges = _git_merge_log(since)
    except Exception as exc:
        print(f"[obsidian_changelog_gen] WARN: git log failed: {exc}", file=sys.stderr)
        merges = []

    entries = _build_entries(merges, use_gh=use_gh)
    report = _render_changelog(entries, since, now_utc)

    if args.dry_run:
        print(report)
        return 0

    args.report_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.report_dir / "CHANGELOG_ops.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"[obsidian_changelog_gen] Changelog written: {out_path} ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
