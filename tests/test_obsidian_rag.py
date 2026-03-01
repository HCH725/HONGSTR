from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import obsidian_common  # noqa: E402
import obsidian_lancedb_index  # noqa: E402
import obsidian_rag_lib  # noqa: E402
import obsidian_sync  # noqa: E402


FIXED_NOW = "2026-03-02T10:00:00Z"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _seed_ssot(repo_root: Path) -> None:
    state_dir = repo_root / "data" / "state"
    _write_json(
        state_dir / "daily_report_latest.json",
        {
            "generated_utc": FIXED_NOW,
            "ssot_status": "WARN",
            "refresh_hint": "bash scripts/refresh_state.sh",
            "ssot_components": {
                "regime_signal": {
                    "status": "WARN",
                    "top_reason": "Coverage is blocked.",
                }
            },
            "freshness_summary": {
                "non_ok_rows": 1,
                "profile_totals": {
                    "backtest": {"ok": 8, "warn": 1, "fail": 0},
                },
            },
            "strategy_pool": {
                "leaderboard_top": [
                    {
                        "strategy_id": "alpha_trend",
                        "candidate_id": "alpha_trend__long__baseline",
                        "family": "trend",
                        "direction": "LONG",
                        "variant": "baseline",
                        "score": 51.2,
                        "oos_mdd": -0.12,
                        "gate_overall": "PASS",
                        "recommendation": "PROMOTE",
                    }
                ]
            },
        },
    )
    _write_json(
        state_dir / "system_health_latest.json",
        {
            "generated_utc": FIXED_NOW,
            "ssot_status": "WARN",
            "components": {
                "coverage_matrix": {"status": "WARN", "blocked": 1, "total": 2},
                "brake": {"status": "WARN"},
            },
        },
    )
    _write_json(
        state_dir / "freshness_table.json",
        {
            "ts_utc": FIXED_NOW,
            "rows": [
                {"symbol": "BTCUSDT", "tf": "1h", "status": "OK"},
                {"symbol": "ETHUSDT", "tf": "4h", "status": "WARN"},
            ],
        },
    )
    _write_json(
        state_dir / "coverage_matrix_latest.json",
        {
            "ts_utc": FIXED_NOW,
            "totals": {"done": 1, "blocked": 1, "rebase": 0, "inProgress": 0},
            "rows": [
                {"symbol": "BTCUSDT", "tf": "1h", "status": "BLOCKED"},
            ],
        },
    )
    _write_json(
        state_dir / "brake_health_latest.json",
        {
            "ts_utc": FIXED_NOW,
            "status": "WARN",
            "overall_fail": True,
        },
    )
    _write_json(
        state_dir / "regime_monitor_latest.json",
        {
            "ts_utc": FIXED_NOW,
            "overall": "WARN",
            "reason": ["Coverage is blocked."],
            "suggestion": "Pause promotions.",
        },
    )
    _write_json(
        state_dir / "strategy_pool.json",
        {
            "generated_utc": FIXED_NOW,
            "report_only": True,
            "candidates": [
                {
                    "strategy_id": "alpha_trend",
                    "candidate_id": "alpha_trend__long__baseline",
                    "family": "trend",
                    "direction": "LONG",
                    "variant": "baseline",
                    "last_score": 51.2,
                    "gate_overall": "PASS",
                    "recommendation": "PROMOTE",
                    "last_oos_metrics": {"sharpe": 0.8, "return": 1.2, "mdd": -0.12},
                }
            ],
            "promoted": ["alpha_trend__long__baseline"],
            "demoted": [],
        },
    )


def test_utc_helpers_return_aware_utc() -> None:
    current = obsidian_common.utc_now()
    assert current.tzinfo == obsidian_common.UTC
    assert current.utcoffset() == timedelta(0)

    naive = datetime(2026, 3, 2, 10, 0, 0)
    normalized_naive = obsidian_common.ensure_aware_utc(naive)
    assert normalized_naive.tzinfo == obsidian_common.UTC
    assert normalized_naive.hour == 10

    taipei = timezone(timedelta(hours=8))
    aware = datetime(2026, 3, 2, 18, 0, 0, tzinfo=taipei)
    normalized_aware = obsidian_common.ensure_aware_utc(aware)
    assert normalized_aware.tzinfo == obsidian_common.UTC
    assert normalized_aware.hour == 10


def test_obsidian_common_has_no_datetime_utc_regression() -> None:
    source = Path(obsidian_common.__file__).read_text(encoding="utf-8")
    import_prefix = "from datetime import "
    attr_prefix = "datetime."
    utc_name = "UTC"
    bad_import = import_prefix + utc_name
    bad_attr = attr_prefix + utc_name
    assert bad_import not in source
    assert bad_attr not in source


def test_obsidian_sync_writes_deterministic_notes(tmp_path: Path) -> None:
    _seed_ssot(tmp_path)

    result = obsidian_sync.sync_obsidian_notes(
        repo_root=tmp_path,
        now_utc=FIXED_NOW,
        write_strategies=True,
        write_incidents=True,
        dry_run=False,
    )

    assert result["changed"] >= 3
    daily_note = tmp_path / "_local" / "obsidian_vault" / "HONGSTR" / "Daily" / "2026" / "03" / "2026-03-02.md"
    strategy_note = tmp_path / "_local" / "obsidian_vault" / "HONGSTR" / "Strategies" / "alpha_trend.md"
    incident_note = tmp_path / "_local" / "obsidian_vault" / "HONGSTR" / "Incidents" / "2026-03-02_coverage-blocked.md"

    assert daily_note.exists()
    assert strategy_note.exists()
    assert incident_note.exists()

    daily_text = daily_note.read_text(encoding="utf-8")
    assert 'type: "daily"' in daily_text
    for heading in (
        "# Summary",
        "# SystemHealth",
        "# DataQuality",
        "# Coverage",
        "# RegimeSignal",
        "# StrategyTop",
        "# ActionsNext",
    ):
        assert heading in daily_text
    assert "data/state/daily_report_latest.json" in daily_text
    assert "ssot_ts_utc" in daily_text


def test_obsidian_sync_is_noop_when_ssot_is_unchanged(tmp_path: Path) -> None:
    _seed_ssot(tmp_path)

    first = obsidian_sync.sync_obsidian_notes(
        repo_root=tmp_path,
        now_utc=FIXED_NOW,
        write_strategies=True,
        write_incidents=True,
        dry_run=False,
    )

    daily_note = tmp_path / "_local" / "obsidian_vault" / "HONGSTR" / "Daily" / "2026" / "03" / "2026-03-02.md"
    state_path = tmp_path / "_local" / "obsidian_index_state.json"
    first_note_bytes = daily_note.read_bytes()
    first_state_bytes = state_path.read_bytes()

    second = obsidian_sync.sync_obsidian_notes(
        repo_root=tmp_path,
        now_utc="2026-03-02T11:00:00Z",
        write_strategies=True,
        write_incidents=True,
        dry_run=False,
    )

    assert first["changed"] >= 3
    assert second["changed"] == 0
    assert daily_note.read_bytes() == first_note_bytes
    assert state_path.read_bytes() == first_state_bytes


def test_build_note_chunks_is_deterministic() -> None:
    note_text = """---
type: "daily"
date: "2026-03-02"
symbols:
  - "BTCUSDT"
---

# Summary
- Coverage blocked on BTC.

# Coverage
- The current coverage blocker is waiting on rebase.
- Another sentence to force a longer section for deterministic chunking.
"""

    first = obsidian_common.build_note_chunks("Daily/2026/03/2026-03-02.md", note_text, max_chars=80, overlap=10)
    second = obsidian_common.build_note_chunks("Daily/2026/03/2026-03-02.md", note_text, max_chars=80, overlap=10)

    assert [chunk.chunk_hash for chunk in first] == [chunk.chunk_hash for chunk in second]
    assert [chunk.heading_path for chunk in first] == [chunk.heading_path for chunk in second]
    assert first


def test_rag_search_returns_ranked_chunks_with_pointers(tmp_path: Path) -> None:
    db_dir = tmp_path / "_local" / "lancedb" / "hongstr_obsidian.lancedb"
    rows = [
        {
            "id": "a",
            "vault_rel_path": "Daily/2026/03/2026-03-02.md",
            "heading_path": "Daily/2026/03/2026-03-02.md#Summary",
            "chunk_text": "Freshness status is WARN and coverage remains blocked for BTCUSDT.",
            "chunk_hash": "hash-a",
            "created_utc": FIXED_NOW,
            "metadata": {"type": "daily", "date": "2026-03-02"},
            "embedding": [],
        },
        {
            "id": "b",
            "vault_rel_path": "Strategies/alpha_trend.md",
            "heading_path": "Strategies/alpha_trend.md#Evidence",
            "chunk_text": "Alpha trend evidence focuses on Sharpe and MDD, not freshness.",
            "chunk_hash": "hash-b",
            "created_utc": FIXED_NOW,
            "metadata": {"type": "strategy", "strategy_id": "alpha_trend"},
            "embedding": [],
        },
    ]
    obsidian_common.save_index_rows(
        db_dir,
        rows,
        provider_name="ollama",
        ollama_model="nomic-embed-text",
    )

    payload = obsidian_rag_lib.rag_search_from_repo(
        tmp_path,
        query="freshness status",
        k=5,
        filter_type="daily",
        since_date="2026-03-01",
    )

    assert payload["status"] == "OK"
    assert payload["provider"] == "lancedb"
    assert payload["db_path"] == "_local/lancedb/hongstr_obsidian.lancedb"
    assert len(payload["chunks"]) == 1
    top = payload["chunks"][0]
    assert top["pointer"] == "Daily/2026/03/2026-03-02.md#Summary"
    assert top["vault_rel_path"] == "Daily/2026/03/2026-03-02.md"
    assert "Freshness status is WARN" in top["text"]


def test_index_dedupes_and_updates_changed_note(tmp_path: Path) -> None:
    vault_root = tmp_path / "_local" / "obsidian_vault" / "HONGSTR"
    note_path = vault_root / "Daily" / "2026" / "03" / "2026-03-02.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        """---
type: "daily"
date: "2026-03-02"
ssot_refs:
  - "data/state/coverage_matrix_latest.json"
---

# Summary
- Coverage blocked on BTC.

# Coverage
- Coverage blocked because one row is BLOCKED.
""",
        encoding="utf-8",
    )

    first = obsidian_lancedb_index.index_obsidian_vault(
        repo_root=tmp_path,
        rebuild=True,
        provider_name="fallback",
    )
    first_rows = obsidian_common.load_index_rows(
        tmp_path / "_local" / "lancedb" / "hongstr_obsidian.lancedb"
    )

    second = obsidian_lancedb_index.index_obsidian_vault(
        repo_root=tmp_path,
        rebuild=False,
        provider_name="fallback",
    )
    second_rows = obsidian_common.load_index_rows(
        tmp_path / "_local" / "lancedb" / "hongstr_obsidian.lancedb"
    )

    assert first["rows"] == len(first_rows)
    assert second["changed_files"] == 0
    assert [row["chunk_hash"] for row in first_rows] == [row["chunk_hash"] for row in second_rows]

    note_path.write_text(
        note_path.read_text(encoding="utf-8").replace(
            "Coverage blocked because one row is BLOCKED.",
            "Coverage blocked because one row is still BLOCKED after recheck.",
        ),
        encoding="utf-8",
    )

    third = obsidian_lancedb_index.index_obsidian_vault(
        repo_root=tmp_path,
        rebuild=False,
        provider_name="fallback",
    )
    third_rows = obsidian_common.load_index_rows(
        tmp_path / "_local" / "lancedb" / "hongstr_obsidian.lancedb"
    )

    assert third["changed_files"] == 1
    assert len(third_rows) == len(first_rows)
    assert [row["chunk_hash"] for row in third_rows] != [row["chunk_hash"] for row in first_rows]
