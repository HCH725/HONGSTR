#!/usr/bin/env python3
"""KB Sync GitHub PRs – poll merged PRs → write Obsidian KB notes.

Usage:
    python scripts/kb_sync_github_prs.py [--repo-root /path] [--dry-run] [--limit N]

Reads: GITHUB_TOKEN or GH_TOKEN from environment.
Writes: _local/obsidian_vault/HONGSTR/KB/PR/YYYY/PR-####.md
State:  _local/obsidian_vault/HONGSTR/KB/_meta/kb_sync_state.json

No external dependencies – stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_OWNER = "HCH725"
REPO_NAME = "HONGSTR"
REPO_SLUG = f"{REPO_OWNER}/{REPO_NAME}"
GITHUB_API = "https://api.github.com"
DEFAULT_PER_PAGE = 100
DEFAULT_LIMIT = 50
TOUCHED_FILES_TOP = 20
FILES_CHANGED_MAX_LINES = 200

_REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
_VAULT_REL = Path("_local/obsidian_vault/HONGSTR")
_KB_REL = _VAULT_REL / "KB"
_VAULT_META_REL = _VAULT_REL / "_meta"
_KB_META_REL = _KB_REL / "_meta"
_PR_REL = _KB_REL / "PR"

UTC = timezone.utc


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _default_state() -> dict[str, Any]:
    return {
        "last_merged_at_utc": None,
        "last_run_utc": None,
        "last_status": None,
        "last_error": None,
    }


def _load_state(meta_dirs: list[Path]) -> dict[str, Any]:
    for meta_dir in meta_dirs:
        path = meta_dir / "kb_sync_state.json"
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            continue
    return _default_state()


def _save_state(meta_dirs: list[Path], state: dict[str, Any]) -> None:
    write_errors: list[str] = []
    write_count = 0
    for meta_dir in meta_dirs:
        path = meta_dir / "kb_sync_state.json"
        try:
            meta_dir.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            tmp.replace(path)
            write_count += 1
        except OSError as exc:
            write_errors.append(f"{path}: {exc}")
    if write_count == 0 and write_errors:
        raise OSError("; ".join(write_errors))


def _now_utc_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        # GitHub uses Z suffix
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _make_request(url: str, token: str) -> tuple[Any, dict[str, str]]:
    """Return (parsed_json, response_headers). Raises on non-2xx."""
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"hongstr-kb-sync/1.0 ({REPO_SLUG})",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return body, headers


def _parse_next_link(link_header: str | None) -> str | None:
    """Extract next-page URL from GitHub Link header, or None."""
    if not link_header:
        return None
    for part in link_header.split(","):
        part = part.strip()
        m = re.match(r'<([^>]+)>;\s*rel="next"', part)
        if m:
            return m.group(1)
    return None


def _fetch_all_pages(url: str, token: str) -> list[Any]:
    """Paginate via Link header until empty or no next."""
    results: list[Any] = []
    current = url
    while current:
        try:
            data, headers = _make_request(current, token)
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429):
                raise RateLimitError(f"Rate limit hit: HTTP {exc.code} on {current}") from exc
            raise
        if not isinstance(data, list):
            break
        if not data:
            break
        results.extend(data)
        next_url = _parse_next_link(headers.get("link"))
        if not next_url:
            break
        current = next_url
    return results


class RateLimitError(Exception):
    """Raised when GitHub signals a rate limit (403/429)."""


# ---------------------------------------------------------------------------
# PR fetching
# ---------------------------------------------------------------------------

def _fetch_closed_prs(token: str, cursor_dt: datetime | None) -> list[dict[str, Any]]:
    """Fetch all closed PRs merged after cursor_dt, up to DEFAULT_LIMIT."""
    url = (
        f"{GITHUB_API}/repos/{REPO_SLUG}/pulls"
        f"?state=closed&base=main&sort=updated&direction=desc&per_page={DEFAULT_PER_PAGE}"
    )
    # We fetch broadly and filter; GitHub doesn't support filtering by merged_at directly.
    all_prs = _fetch_all_pages(url, token)

    merged: list[dict[str, Any]] = []
    for pr in all_prs:
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue
        if cursor_dt is not None:
            merged_at_dt = _parse_iso(merged_at)
            if merged_at_dt is None or merged_at_dt <= cursor_dt:
                continue
        if pr.get("base", {}).get("ref") != "main":
            continue
        merged.append(pr)

    # Sort ascending by merged_at so we process oldest-first
    merged.sort(key=lambda p: p.get("merged_at", ""))
    return merged


def _fetch_pr_files(token: str, pr_number: int) -> list[dict[str, Any]]:
    url = (
        f"{GITHUB_API}/repos/{REPO_SLUG}/pulls/{pr_number}/files"
        f"?per_page={DEFAULT_PER_PAGE}"
    )
    return _fetch_all_pages(url, token)


# ---------------------------------------------------------------------------
# Note generation
# ---------------------------------------------------------------------------

def _extract_summary_bullets(title: str, body: str | None) -> list[str]:
    """Produce 3–8 summary bullets from title + body (no LLM)."""
    bullets: list[str] = []
    # Title always becomes first bullet
    bullets.append(title.strip())

    if body:
        # Take first block of non-empty lines up to 7 more bullets
        for raw in body.splitlines():
            line = raw.strip()
            if not line:
                if bullets:
                    break  # stop at first blank line after content
                continue
            # Skip markdown headings / horizontal rules
            if line.startswith("#") or line.startswith("---") or line.startswith("==="):
                continue
            # Strip leading bullet markers
            cleaned = re.sub(r"^[-*•]\s+", "", line)
            if cleaned and cleaned not in bullets:
                bullets.append(cleaned)
            if len(bullets) >= 8:
                break

    return bullets[:8]


def _extract_why(body: str | None) -> str:
    """Extract the first 3 paragraphs from PR body as 'Why'."""
    if not body:
        return ""
    paragraphs: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        if line.strip():
            current.append(line)
        else:
            if current:
                paragraphs.append("\n".join(current))
                current = []
            if len(paragraphs) >= 3:
                break
    if current:
        paragraphs.append("\n".join(current))
    return "\n\n".join(paragraphs[:3])


def _extract_verification(body: str | None) -> str:
    """Look for CI / verification hints in PR body."""
    if not body:
        return "CI: see PR checks"
    lower = body.lower()
    if any(kw in lower for kw in ("pytest", "ci:", "github actions", "check", "test", "verify", "bash ")):
        # Return lines that look like commands or CI mentions (up to 10)
        lines: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if any(
                kw in stripped.lower()
                for kw in ("pytest", "ci:", "actions", "check", "bash ", "make ", "test", "verify")
            ):
                lines.append(stripped)
            if len(lines) >= 10:
                break
        if lines:
            return "\n".join(lines)
    return "CI: see PR checks"


def _build_files_section(files: list[dict[str, Any]]) -> str:
    """Build the Files Changed section, capped at FILES_CHANGED_MAX_LINES lines."""
    lines: list[str] = []
    for f in files:
        path = f.get("filename", "?")
        add = f.get("additions", 0)
        delete = f.get("deletions", 0)
        lines.append(f"- `{path}` +{add}/−{delete}")
        if len(lines) >= FILES_CHANGED_MAX_LINES:
            lines.append("*(truncated)*")
            break
    return "\n".join(lines)


def _build_note(pr: dict[str, Any], files: list[dict[str, Any]]) -> str:
    """Generate the full Obsidian Markdown note for a merged PR."""
    number: int = pr["number"]
    title: str = pr.get("title", "")
    author: str = (pr.get("user") or {}).get("login", "unknown")
    merged_at: str = pr.get("merged_at", "")
    sha: str = pr.get("merge_commit_sha", "")
    base_ref: str = (pr.get("base") or {}).get("ref", "")
    head_ref: str = (pr.get("head") or {}).get("ref", "")
    labels: list[str] = [lb["name"] for lb in (pr.get("labels") or [])]
    html_url: str = pr.get("html_url", "")
    body: str | None = pr.get("body")

    additions = sum(f.get("additions", 0) for f in files)
    deletions = sum(f.get("deletions", 0) for f in files)
    top_files = [f.get("filename", "") for f in files[:TOUCHED_FILES_TOP]]

    labels_yaml = (
        "[" + ", ".join(f'"{lb}"' for lb in labels) + "]"
        if labels
        else "[]"
    )
    top_files_yaml = (
        "\n" + "".join(f'  - "{p}"\n' for p in top_files)
        if top_files
        else " []"
    )

    summary_bullets = _extract_summary_bullets(title, body)
    summary_md = "\n".join(f"- {b}" for b in summary_bullets)

    why_text = _extract_why(body)
    why_section = f"\n## Why\n\n{why_text}\n" if why_text.strip() else ""

    files_section = _build_files_section(files)
    verification = _extract_verification(body)

    note = textwrap.dedent(f"""\
        ---
        type: pr_note
        repo: {REPO_SLUG}
        pr_number: {number}
        title: "{title.replace('"', "'")}"
        author: "{author}"
        merged_at_utc: "{merged_at}"
        merge_commit_sha: "{sha}"
        base_branch: "{base_ref}"
        head_branch: "{head_ref}"
        labels: {labels_yaml}
        files_changed_count: {len(files)}
        additions_total: {additions}
        deletions_total: {deletions}
        touched_files_top:{top_files_yaml}
        links:
          pr: "{html_url}"
          rollback:
            git_revert: "git revert {sha}"
        ---

        # PR-{number:04d}: {title}

        ## Summary

        {summary_md}
        {why_section}
        ## Files Changed

        {files_section}

        ## Verification

        {verification}

        ## Rollback

        ```bash
        git revert {sha}
        ```
    """)
    return note


# ---------------------------------------------------------------------------
# Note path
# ---------------------------------------------------------------------------

def _note_path(kb_pr_dir: Path, pr: dict[str, Any]) -> Path:
    number: int = pr["number"]
    merged_at: str = pr.get("merged_at", "")
    year = merged_at[:4] if len(merged_at) >= 4 else "0000"
    return kb_pr_dir / year / f"PR-{number:04d}.md"


# ---------------------------------------------------------------------------
# Main sync logic
# ---------------------------------------------------------------------------

def sync_prs(
    repo_root: Path,
    token: str,
    dry_run: bool = False,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    meta_dirs = [repo_root / _VAULT_META_REL, repo_root / _KB_META_REL]
    kb_pr_dir = repo_root / _PR_REL

    if not dry_run:
        for meta_dir in meta_dirs:
            meta_dir.mkdir(parents=True, exist_ok=True)
        kb_pr_dir.mkdir(parents=True, exist_ok=True)

    state = _load_state(meta_dirs)
    cursor_raw: str | None = state.get("last_merged_at_utc")
    cursor_dt = _parse_iso(cursor_raw)

    run_utc = _now_utc_iso()
    written = 0
    skipped = 0
    warnings: list[str] = []
    max_written_merged_at: str | None = None
    final_status = "OK"

    try:
        candidate_prs = _fetch_closed_prs(token, cursor_dt)
    except RateLimitError as exc:
        warnings.append(f"WARN rate_limit: {exc}")
        state.update({"last_run_utc": run_utc, "last_status": "WARN", "last_error": str(exc)})
        if not dry_run:
            _save_state(meta_dirs, state)
        return {
            "written": 0,
            "skipped": 0,
            "status": "WARN",
            "warnings": warnings,
        }

    # Apply per-run cap
    candidate_prs = candidate_prs[:limit]

    for pr in candidate_prs:
        number = pr["number"]
        merged_at_str: str = pr.get("merged_at", "")
        note_path = _note_path(kb_pr_dir, pr)

        # Dedup: skip if file already exists
        if note_path.exists():
            skipped += 1
            continue

        # Fetch files with pagination + rate-limit handling
        try:
            files = _fetch_pr_files(token, number)
        except RateLimitError as exc:
            warnings.append(f"WARN rate_limit PR#{number}: {exc}")
            final_status = "WARN"
            continue
        except Exception as exc:
            warnings.append(f"WARN fetch_files PR#{number}: {exc}")
            final_status = "WARN"
            continue

        note_content = _build_note(pr, files)

        if dry_run:
            written += 1
            # Track max merged_at of would-be writes
            if not max_written_merged_at or merged_at_str > max_written_merged_at:
                max_written_merged_at = merged_at_str
            continue

        try:
            note_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = note_path.with_suffix(".tmp")
            tmp_path.write_text(note_content, encoding="utf-8")
            tmp_path.replace(note_path)
            written += 1
            if not max_written_merged_at or merged_at_str > max_written_merged_at:
                max_written_merged_at = merged_at_str
        except OSError as exc:
            warnings.append(f"WARN write PR#{number}: {exc}")
            final_status = "WARN"

    # Cursor advance: only to max merged_at of successfully written notes
    # If zero notes written → do NOT advance cursor
    if max_written_merged_at:
        state["last_merged_at_utc"] = max_written_merged_at

    state["last_run_utc"] = run_utc
    state["last_status"] = final_status
    state["last_error"] = warnings[-1] if warnings else None

    if not dry_run:
        _save_state(meta_dirs, state)

    return {
        "written": written,
        "skipped": skipped,
        "status": final_status,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT_DEFAULT,
        help="Path to repo root (default: auto-detected)",
    )
    p.add_argument("--dry-run", action="store_true", help="Compute without writing notes or state")
    p.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max PRs to process per run (default: {DEFAULT_LIMIT})",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if not token:
        print(
            json.dumps({"status": "FAIL", "error": "GITHUB_TOKEN / GH_TOKEN not set"}),
            file=sys.stderr,
        )
        return 1

    result = sync_prs(repo_root=args.repo_root, token=token, dry_run=args.dry_run, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in ("OK", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())
