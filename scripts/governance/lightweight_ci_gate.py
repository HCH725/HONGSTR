#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
from pathlib import Path


REQUIRED_SECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Stage", r"(?im)^##\s+Stage\s*$"),
    ("Checklist item", r"(?im)^##\s+Checklist item\s*$"),
    ("Plane", r"(?im)^##\s+Plane\s*$"),
    ("DoD improved", r"(?im)^##\s+DoD improved\s*$"),
    ("Summary of change", r"(?im)^##\s+Summary of change\s*$"),
    ("Files changed", r"(?im)^##\s+Files changed\s*$"),
    ("Allowed paths", r"(?im)^##\s+Allowed paths\s*$"),
    ("Forbidden paths", r"(?im)^##\s+Forbidden paths\s*$"),
    ("Evidence", r"(?im)^##\s+Evidence\s*$"),
    ("Tests run", r"(?im)^##\s+Tests run\s*$"),
    (
        "Expected SSOT/output impact",
        r"(?im)^##\s+Expected SSOT/output impact\s*$",
    ),
    ("Degrade", r"(?im)^##\s+Degrade\s*$"),
    ("Kill switch / rollback", r"(?im)^##\s+Kill switch / rollback\s*$"),
    ("Legacy Impact", r"(?im)^##\s+Legacy Impact(?:\s*\(.*\))?\s*$"),
    ("Out of scope / not changed", r"(?im)^##\s+Out of scope / not changed\s*$"),
)

GOVERNANCE_SIGNAL_PATTERNS: tuple[str, ...] = (
    "AGENTS.md",
    ".agents/**",
    ".github/**",
    ".opencode/**",
    "docs/**",
    "scripts/guardrail_check.sh",
    "scripts/governance/**",
    "tests/test_lightweight_ci_gate.py",
)

GOVERNANCE_ALLOWED_PATTERNS: tuple[str, ...] = (
    "AGENTS.md",
    ".agents/**",
    ".github/**",
    ".opencode/**",
    "docs/**",
    "scripts/**",
    "tests/**",
)

GOVERNANCE_FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "src/hongstr/**",
    "data/**",
    "_local/**",
    ".env",
    ".env.*",
    "launchd/**",
    "web/**",
    "research/**",
    ".pytest_cache/**",
    ".ruff_cache/**",
    "__pycache__/**",
    "logs/**",
    "reports/**",
    "tmp/**",
    "*.parquet",
    "*.pkl",
    "*.pickle",
    "*.joblib",
    "*.onnx",
    "*.pt",
    "*.ckpt",
    "*.npz",
)

GOVERNANCE_BODY_SIGNAL_RE = re.compile(
    r"(?i)\bStage 0\b|\bGovernance\b|\bdocs-first\b|\blightweight CI\b"
)


def _normalize_pattern(pattern: str) -> str:
    return str(pattern or "").strip().strip("`").replace("\\", "/")


def _matches_pattern(path: str, pattern: str) -> bool:
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


def _collect_changed_paths(changed_files_file: str | None = None) -> list[str]:
    if changed_files_file:
        return [
            line.strip()
            for line in Path(changed_files_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

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


def _load_pr_body(pr_body_file: str | None = None) -> tuple[str, bool]:
    explicit_pr_body = os.environ.get("PR_BODY")
    explicit_pr_body_file = os.environ.get("PR_BODY_FILE")
    if pr_body_file:
        return Path(pr_body_file).read_text(encoding="utf-8"), True
    if explicit_pr_body_file:
        return Path(explicit_pr_body_file).read_text(encoding="utf-8"), True
    if explicit_pr_body is not None:
        return explicit_pr_body, True

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if not event_path:
        return "", False

    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    has_pr_context = event_name.startswith("pull_request") or "pull_request" in payload
    if "pull_request" in payload:
        body = payload.get("pull_request", {}).get("body")
        return (body if isinstance(body, str) else ""), has_pr_context
    if "issue" in payload:
        body = payload.get("issue", {}).get("body")
        return (body if isinstance(body, str) else ""), has_pr_context
    return "", has_pr_context


def _missing_sections(content: str, required_sections: tuple[tuple[str, str], ...]) -> list[str]:
    text = content or ""
    missing: list[str] = []
    for label, pattern in required_sections:
        if not re.search(pattern, text):
            missing.append(label)
    return missing


def _is_governance_candidate(paths: list[str], pr_body: str) -> bool:
    if any(
        _matches_pattern(path, pattern)
        for path in paths
        for pattern in GOVERNANCE_SIGNAL_PATTERNS
    ):
        return True
    return bool(pr_body and GOVERNANCE_BODY_SIGNAL_RE.search(pr_body))


def _split_governance_path_violations(paths: list[str]) -> tuple[list[str], list[str]]:
    forbidden: list[str] = []
    outside_allowed: list[str] = []
    for path in paths:
        if any(_matches_pattern(path, pattern) for pattern in GOVERNANCE_FORBIDDEN_PATTERNS):
            forbidden.append(path)
        elif not any(_matches_pattern(path, pattern) for pattern in GOVERNANCE_ALLOWED_PATTERNS):
            outside_allowed.append(path)
    return forbidden, outside_allowed


def _format_issue(title: str, items: list[str]) -> str:
    lines = [title]
    lines.extend(f"  - {item}" for item in items)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lightweight docs/governance gate for PR body and path scope."
    )
    parser.add_argument(
        "--template-path",
        default=".github/pull_request_template.md",
        help="Path to the root PR template file.",
    )
    parser.add_argument(
        "--changed-files-file",
        help="Optional newline-delimited file containing changed paths.",
    )
    parser.add_argument(
        "--pr-body-file",
        help="Optional file containing the PR body markdown.",
    )
    args = parser.parse_args(argv)

    issues: list[str] = []
    notes: list[str] = []

    template_path = Path(args.template_path)
    if not template_path.is_file():
        issues.append(f"PR template not found: {template_path}")
    else:
        missing_template_sections = _missing_sections(
            template_path.read_text(encoding="utf-8"), REQUIRED_SECTION_PATTERNS
        )
        if missing_template_sections:
            issues.append(
                _format_issue(
                    "PR template is missing required sections:",
                    missing_template_sections,
                )
            )

    changed_paths = _collect_changed_paths(args.changed_files_file)
    if not changed_paths:
        print("governance_gate: no changed files detected")
        return 0

    pr_body, has_pr_context = _load_pr_body(args.pr_body_file)
    governance_candidate = _is_governance_candidate(changed_paths, pr_body)

    if governance_candidate:
        forbidden_paths, outside_allowed = _split_governance_path_violations(changed_paths)
        if forbidden_paths:
            issues.append(
                _format_issue(
                    "Docs/governance scope touched forbidden paths:",
                    forbidden_paths,
                )
            )
        if outside_allowed:
            issues.append(
                _format_issue(
                    "Docs/governance scope touched paths outside the allowed lightweight gate scope:",
                    outside_allowed,
                )
            )
        if pr_body.strip():
            missing_pr_sections = _missing_sections(pr_body, REQUIRED_SECTION_PATTERNS)
            if missing_pr_sections:
                issues.append(
                    _format_issue(
                        "PR body is missing required governance sections:",
                        missing_pr_sections,
                    )
                )
        elif has_pr_context:
            issues.append(
                "Pull request body is missing or unreadable. Expected the root template sections."
            )
        else:
            notes.append("PR body check skipped locally (no pull_request body context).")
    else:
        notes.append("Governance-specific path/body checks skipped (no docs/governance scope detected).")

    if issues:
        print("governance_gate: FAIL")
        for issue in issues:
            print(issue)
        for note in notes:
            print(f"note: {note}")
        return 1

    scope = "governance" if governance_candidate else "generic"
    print(f"governance_gate: PASS (scope={scope}, files={len(changed_paths)})")
    for note in notes:
        print(f"note: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
