"""Unit tests for scripts/obsidian_ssot_daily.py

Tests:
1. Graceful WARN when all SSOT files missing (exit 0, no file written)
2. Fixed headings present in output
3. Frontmatter keys present
4. Idempotent write (same content → file not re-written)
5. DataCatalog section has content when changes file exists
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Add scripts/ to sys.path
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import obsidian_ssot_daily as osd  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _seed_state(state_dir: Path) -> None:
    """Write minimal but valid SSOT files."""
    _write_json(
        state_dir / "system_health_latest.json",
        {
            "ts_utc": "2026-03-04T01:00:00Z",
            "ssot_status": "WARN",
            "components": {
                "coverage_matrix": {"status": "WARN", "blocked": 1, "total": 5},
                "brake": {"status": "OK"},
            },
        },
    )
    _write_json(
        state_dir / "freshness_table.json",
        {
            "ts_utc": "2026-03-04T01:00:00Z",
            "rows": [
                {"symbol": "BTCUSDT", "tf": "1h", "status": "OK"},
                {"symbol": "ETHUSDT", "tf": "4h", "status": "WARN"},
            ],
        },
    )
    _write_json(
        state_dir / "coverage_matrix_latest.json",
        {
            "ts_utc": "2026-03-04T01:00:00Z",
            "totals": {"done": 4, "blocked": 1, "rebase": 0, "inProgress": 0},
            "rows": [
                {"symbol": "BTCUSDT", "tf": "1h", "status": "BLOCKED"},
            ],
        },
    )
    _write_json(
        state_dir / "regime_monitor_latest.json",
        {
            "ts_utc": "2026-03-04T01:00:00Z",
            "overall": "WARN",
            "reason": ["Coverage is blocked."],
            "suggestion": "Pause promotions.",
        },
    )


# ---------------------------------------------------------------------------
# 1. Graceful WARN when all files missing
# ---------------------------------------------------------------------------

def test_graceful_warn_when_all_files_missing(tmp_path: Path) -> None:
    """No data/state files → returns WARN, exit 0, no note file written."""
    result = osd.export_ssot_daily(repo_root=tmp_path, dry_run=False)

    assert result["status"] == "WARN"
    assert result["written"] is False
    assert result.get("reason") == "all_files_missing"

    # No note file should be created anywhere
    kb_dir = tmp_path / "_local/obsidian_vault/HONGSTR/KB/SSOT/Daily"
    assert not any(kb_dir.rglob("*.md")) if kb_dir.exists() else True


# ---------------------------------------------------------------------------
# 2. Fixed headings present in output
# ---------------------------------------------------------------------------

def test_fixed_headings_present(tmp_path: Path) -> None:
    """Written note must contain all 6 fixed ## headings."""
    state_dir = tmp_path / "data" / "state"
    _seed_state(state_dir)

    result = osd.export_ssot_daily(repo_root=tmp_path)
    assert result["written"] is True

    note_path = Path(result["path"])
    content = note_path.read_text(encoding="utf-8")

    for heading in (
        "## SystemHealth",
        "## Freshness",
        "## Coverage",
        "## RegimeSignal",
        "## DataCatalog Changes",
        "## Action Hints",
    ):
        assert heading in content, f"Missing heading: {heading!r}"


# ---------------------------------------------------------------------------
# 3. Frontmatter keys present
# ---------------------------------------------------------------------------

def test_frontmatter_keys_present(tmp_path: Path) -> None:
    """Written note must have all required frontmatter keys."""
    state_dir = tmp_path / "data" / "state"
    _seed_state(state_dir)

    result = osd.export_ssot_daily(repo_root=tmp_path)
    assert result["written"] is True

    note_path = Path(result["path"])
    content = note_path.read_text(encoding="utf-8")

    # Check YAML frontmatter block is present + keys
    assert content.startswith("---\n"), "Note must start with YAML frontmatter"
    assert "type: daily_ssot" in content
    assert "date:" in content
    assert "ts_utc:" in content
    assert "status_summary:" in content
    assert "components:" in content
    assert "ssot_refs:" in content


# ---------------------------------------------------------------------------
# 4. Idempotent write (same content → skip re-write)
# ---------------------------------------------------------------------------

def test_idempotent_write(tmp_path: Path) -> None:
    """Calling export twice with same data must not re-write the note."""
    state_dir = tmp_path / "data" / "state"
    _seed_state(state_dir)

    # First write
    result1 = osd.export_ssot_daily(repo_root=tmp_path)
    assert result1["written"] is True

    note_path = Path(result1["path"])
    mtime_after_first = note_path.stat().st_mtime

    # Second write – same data, same content
    result2 = osd.export_ssot_daily(repo_root=tmp_path)
    assert result2["written"] is False
    assert result2.get("reason") == "unchanged"

    # File must not have been touched
    mtime_after_second = note_path.stat().st_mtime
    assert mtime_after_second == mtime_after_first, (
        "File should not be re-written when content is identical"
    )


# ---------------------------------------------------------------------------
# 5. DataCatalog section has content when changes file exists
# ---------------------------------------------------------------------------

def test_data_catalog_section_has_content(tmp_path: Path) -> None:
    """When data_catalog_changes_latest.json has entries, they appear in the note."""
    state_dir = tmp_path / "data" / "state"
    _seed_state(state_dir)

    # Add catalog + changes
    _write_json(
        state_dir / "data_catalog_latest.json",
        {
            "ts_utc": "2026-03-04T01:00:00Z",
            "datasets": [{"id": "btc_1h_klines"}, {"id": "eth_4h_klines"}],
        },
    )
    _write_json(
        state_dir / "data_catalog_changes_latest.json",
        {
            "ts_utc": "2026-03-04T01:00:00Z",
            "added": ["futures_metrics_v2"],
            "removed": [],
            "modified": ["btc_1h_klines"],
        },
    )

    result = osd.export_ssot_daily(repo_root=tmp_path)
    assert result["written"] is True

    content = Path(result["path"]).read_text(encoding="utf-8")
    assert "## DataCatalog Changes" in content
    assert "futures_metrics_v2" in content, "Added dataset should appear in DataCatalog section"
    assert "btc_1h_klines" in content, "Modified dataset should appear in DataCatalog section"
    assert "Catalog datasets: 2" in content
