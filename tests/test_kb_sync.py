"""Unit tests for kb_sync_github_prs.py

Tests: note path, front-matter schema, cursor non-advance on rate-limit,
       skip-existing dedup, cursor advance on success.

No real HTTP calls – all GitHub responses are mocked.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Add scripts/ to sys.path so we can import the module under test
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import kb_sync_github_prs as ksync  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_FAKE_PR: dict[str, Any] = {
    "number": 42,
    "title": "feat: add KB sync poller",
    "user": {"login": "hong"},
    "merged_at": "2026-03-04T00:00:00Z",
    "merge_commit_sha": "abc1234abc1234abc1234abc1234abc1234abc12",
    "body": "This PR adds the KB sync poller.\n\nIt polls GitHub every hour.",
    "labels": [{"name": "enhancement"}],
    "html_url": "https://github.com/HCH725/HONGSTR/pull/42",
    "base": {"ref": "main"},
    "head": {"ref": "feature/kb-sync"},
    "state": "closed",
}

_FAKE_FILES: list[dict[str, Any]] = [
    {"filename": "scripts/kb_sync_github_prs.py", "additions": 300, "deletions": 0},
    {"filename": "scripts/kb_sync_run.sh", "additions": 80, "deletions": 0},
]


def _make_mock_response(payload: Any, headers: dict | None = None) -> MagicMock:
    """Return a mock object that behaves like urllib.request.urlopen context."""
    data = json.dumps(payload).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = data
    mock_resp.headers = {**(headers or {})}
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# 1. Note path generation
# ---------------------------------------------------------------------------

def test_note_path_generation(tmp_path: Path) -> None:
    kb_pr_dir = tmp_path / "KB" / "PR"
    note = ksync._note_path(kb_pr_dir, _FAKE_PR)
    assert note == kb_pr_dir / "2026" / "PR-0042.md", f"Unexpected path: {note}"


# ---------------------------------------------------------------------------
# 2. Front-matter schema presence
# ---------------------------------------------------------------------------

def test_frontmatter_schema_presence() -> None:
    note_content = ksync._build_note(_FAKE_PR, _FAKE_FILES)

    required_keys = [
        "type: pr_note",
        "repo:",
        "pr_number:",
        "title:",
        "author:",
        "merged_at_utc:",
        "merge_commit_sha:",
        "base_branch:",
        "head_branch:",
        "labels:",
        "files_changed_count:",
        "additions_total:",
        "deletions_total:",
        "touched_files_top:",
        "links:",
        "pr:",
        "rollback:",
        "git_revert:",
    ]
    for key in required_keys:
        assert key in note_content, f"Missing front-matter key: {key!r}"

    # Body sections
    for section in ("## Summary", "## Files Changed", "## Verification", "## Rollback"):
        assert section in note_content, f"Missing body section: {section!r}"


# ---------------------------------------------------------------------------
# 3. Cursor not advanced on rate-limit
# ---------------------------------------------------------------------------

def test_cursor_not_advanced_on_rate_limit(tmp_path: Path) -> None:
    """When the PR list fetch hits a 403, cursor must stay unchanged."""
    kb_meta_dir = tmp_path / "_local/obsidian_vault/HONGSTR/KB/_meta"
    kb_meta_dir.mkdir(parents=True, exist_ok=True)

    initial_state = {
        "last_merged_at_utc": "2026-01-01T00:00:00Z",
        "last_run_utc": None,
        "last_status": None,
        "last_error": None,
    }
    (kb_meta_dir / "kb_sync_state.json").write_text(
        json.dumps(initial_state), encoding="utf-8"
    )

    http_err = urllib.error.HTTPError(
        url="https://api.github.com/...",
        code=403,
        msg="rate limited",
        hdrs=MagicMock(),
        fp=BytesIO(b"{}"),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        result = ksync.sync_prs(repo_root=tmp_path, token="fake_token", dry_run=False)

    assert result["status"] == "WARN"
    assert result["written"] == 0

    # State must not advance cursor
    kb_saved = json.loads((kb_meta_dir / "kb_sync_state.json").read_text())
    assert kb_saved["last_merged_at_utc"] == "2026-01-01T00:00:00Z", (
        "Cursor must not advance on rate-limit"
    )
    vault_saved = json.loads(
        (tmp_path / "_local/obsidian_vault/HONGSTR/_meta/kb_sync_state.json").read_text()
    )
    assert vault_saved["last_merged_at_utc"] == "2026-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# 4. Skip existing note (dedup)
# ---------------------------------------------------------------------------

def test_skip_existing_note(tmp_path: Path) -> None:
    """If PR-0042.md already exists, it must be skipped (written=0, skipped=1)."""
    kb_pr_dir = tmp_path / "_local/obsidian_vault/HONGSTR/KB/PR/2026"
    kb_pr_dir.mkdir(parents=True, exist_ok=True)
    existing = kb_pr_dir / "PR-0042.md"
    existing.write_text("already here", encoding="utf-8")

    # PR list response: one closed+merged PR
    pr_list_resp = _make_mock_response([_FAKE_PR])
    # files response (empty – should not be reached)
    files_resp = _make_mock_response([])

    responses = [pr_list_resp, pr_list_resp, files_resp]  # paginate: 2nd call = empty page

    with patch("urllib.request.urlopen", side_effect=responses):
        result = ksync.sync_prs(repo_root=tmp_path, token="fake_token", dry_run=False)

    assert result["skipped"] == 1
    assert result["written"] == 0


# ---------------------------------------------------------------------------
# 5. Cursor advances on successful write
# ---------------------------------------------------------------------------

def test_cursor_advances_on_success(tmp_path: Path) -> None:
    """After writing one PR note, cursor must advance to that PR's merged_at."""
    # Create vault dirs so no mkdir errors.
    kb_pr_dir = tmp_path / "_local/obsidian_vault/HONGSTR/KB/PR"
    vault_meta_dir = tmp_path / "_local/obsidian_vault/HONGSTR/_meta"
    kb_meta_dir = tmp_path / "_local/obsidian_vault/HONGSTR/KB/_meta"
    kb_pr_dir.mkdir(parents=True, exist_ok=True)
    vault_meta_dir.mkdir(parents=True, exist_ok=True)
    kb_meta_dir.mkdir(parents=True, exist_ok=True)

    # PR list: one new PR (merged after an empty cursor)
    pr_list_page1 = _make_mock_response([_FAKE_PR])
    pr_list_page2 = _make_mock_response([])   # second page: empty → stop
    files_page1   = _make_mock_response(_FAKE_FILES)
    files_page2   = _make_mock_response([])   # second page: empty → stop

    with patch("urllib.request.urlopen", side_effect=[pr_list_page1, pr_list_page2, files_page1, files_page2]):
        result = ksync.sync_prs(repo_root=tmp_path, token="fake_token", dry_run=False)

    assert result["written"] == 1, f"Expected 1 written, got {result}"
    assert result["status"] in ("OK", "WARN")

    vault_state_file = vault_meta_dir / "kb_sync_state.json"
    kb_state_file = kb_meta_dir / "kb_sync_state.json"
    assert vault_state_file.exists(), f"State file not found at {vault_state_file}"
    assert kb_state_file.exists(), f"State file not found at {kb_state_file}"
    vault_saved = json.loads(vault_state_file.read_text())
    kb_saved = json.loads(kb_state_file.read_text())
    assert vault_saved["last_merged_at_utc"] == _FAKE_PR["merged_at"], (
        f"Cursor should be {_FAKE_PR['merged_at']!r}, got {vault_saved['last_merged_at_utc']!r}"
    )
    assert kb_saved["last_merged_at_utc"] == _FAKE_PR["merged_at"], (
        f"Cursor should be {_FAKE_PR['merged_at']!r}, got {kb_saved['last_merged_at_utc']!r}"
    )

    # Verify the note file was actually created
    note_path = kb_pr_dir / "2026" / "PR-0042.md"
    assert note_path.exists(), "PR note file should exist after successful write"
