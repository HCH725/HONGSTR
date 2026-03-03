#!/usr/bin/env python3
"""
scripts/obsidian_link_audit.py
-------------------------------
Scan the local Obsidian vault for notes that are missing required PR/Issue
cross-references, and emit a report-only Markdown file.

Usage:
    python scripts/obsidian_link_audit.py [--vault-root PATH] [--dry-run]

Output:  reports/obsidian_audit/link_audit_YYYYMMDD.md   (NOT committed to git)
Exit:    0 always (report-only; never blocks CI)
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_VAULT_ROOT = REPO_ROOT / "_local" / "obsidian_vault" / "HONGSTR"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports" / "obsidian_audit"

# Note categories that REQUIRE a linked PR or issue
AUDITED_FOLDERS = {"Incidents", "Decisions", "Research"}

# Patterns that count as a PR/issue reference
_PR_PATTERNS = [
    re.compile(r"linked_pr\s*:\s*['\"]?#?\d+", re.I),
    re.compile(r"#pr[:=]\s*\d+", re.I),
    re.compile(r"github\.com/[^/]+/[^/]+/pull/\d+"),
]
_ISSUE_PATTERNS = [
    re.compile(r"linked_issue\s*:\s*['\"]?#?\d+", re.I),
    re.compile(r"#issue[:=]\s*\d+", re.I),
    re.compile(r"github\.com/[^/]+/[^/]+/issues/\d+"),
]

_NONE_VALUE = re.compile(r"""linked_(?:pr|issue)\s*:\s*['""]?\s*(?:none|""|''|)\s*$""", re.I | re.M)


def _has_link(text: str, patterns: list[re.Pattern]) -> bool:
    for pat in patterns:
        if pat.search(text):
            return True
    return False


def _has_none_placeholder(text: str) -> bool:
    return bool(_NONE_VALUE.search(text))


def audit_vault(vault_root: Path) -> list[dict]:
    """Return list of issue dicts for notes that are missing required links."""
    issues: list[dict] = []
    if not vault_root.exists():
        return [{"file": str(vault_root), "issue": "vault_root_missing"}]

    for folder in AUDITED_FOLDERS:
        folder_path = vault_root / folder
        if not folder_path.exists():
            continue
        for note in sorted(folder_path.rglob("*.md")):
            try:
                text = note.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                issues.append({"file": str(note.relative_to(vault_root)), "missing": ["unreadable"]})
                continue

            missing: list[str] = []
            if not _has_link(text, _PR_PATTERNS):
                missing.append("linked_pr")
            if not _has_link(text, _ISSUE_PATTERNS):
                missing.append("linked_issue")

            if missing:
                placeholder = _has_none_placeholder(text)
                issues.append({
                    "file": str(note.relative_to(vault_root)),
                    "missing": missing,
                    "has_none_placeholder": placeholder,
                })

    return issues


def _render_report(issues: list[dict], vault_root: Path, now_utc: str) -> str:
    lines = [
        f"# Obsidian Link Audit Report",
        f"",
        f"**Generated:** {now_utc}  ",
        f"**Vault root:** `{vault_root}`  ",
        f"**Audited categories:** {', '.join(sorted(AUDITED_FOLDERS))}",
        f"",
    ]

    if not issues:
        lines += [
            "## ✅ All notes have required cross-references.",
            "",
            "No issues found.",
        ]
    else:
        total = len(issues)
        with_placeholder = sum(1 for i in issues if i.get("has_none_placeholder"))
        lines += [
            f"## ⚠️ {total} note(s) missing required cross-references",
            f"({with_placeholder} explicitly marked `none`, {total - with_placeholder} need attention)",
            "",
            "| Note | Missing | Has 'none' placeholder? |",
            "|------|---------|------------------------|",
        ]
        for issue in sorted(issues, key=lambda x: x["file"]):
            if "issue" in issue:
                lines.append(f"| `{issue['file']}` | {issue['issue']} | — |")
            else:
                missing_str = ", ".join(f"`{m}`" for m in issue["missing"])
                placeholder = "yes" if issue.get("has_none_placeholder") else "**no — fix required**"
                lines.append(f"| `{issue['file']}` | {missing_str} | {placeholder} |")

        lines += [
            "",
            "## How to Fix",
            "",
            "For each note without a placeholder:",
            "1. Add `linked_pr: \"#NNN\"` to the YAML front-matter, or",
            "2. Add `linked_pr: \"none\"` with a justification comment if no PR exists.",
            "3. Repeat for `linked_issue`.",
        ]

    lines += [""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Obsidian vault cross-reference audit")
    parser.add_argument("--vault-root", type=Path, default=DEFAULT_VAULT_ROOT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Print report to stdout; do not write file")
    args = parser.parse_args(argv)

    now_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")

    issues = audit_vault(args.vault_root)
    report = _render_report(issues, args.vault_root, now_utc)

    if args.dry_run:
        print(report)
        return 0

    args.report_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.report_dir / f"link_audit_{today}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"[obsidian_link_audit] Report written: {out_path}")
    if issues:
        n_critical = sum(1 for i in issues if not i.get("has_none_placeholder") and "issue" not in i)
        if n_critical:
            print(f"[obsidian_link_audit] {n_critical} note(s) need PR/Issue links added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
