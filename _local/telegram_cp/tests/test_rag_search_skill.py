from __future__ import annotations

from pathlib import Path

from _local.telegram_cp.args_schema import parse_args
from _local.telegram_cp.skills.rag_search import run_rag_search
from scripts.obsidian_common import save_index_rows


def _seed_index(repo: Path) -> None:
    db_dir = repo / "_local" / "lancedb" / "hongstr_obsidian.lancedb"
    rows = [
        {
            "id": "chunk-1",
            "vault_rel_path": "Daily/2026/03/2026-03-02.md",
            "heading_path": "Daily/2026/03/2026-03-02.md#Summary",
            "chunk_text": "Freshness status is WARN and the ETL backlog needs review.",
            "chunk_hash": "hash-1",
            "created_utc": "2026-03-02T10:00:00Z",
            "metadata": {"type": "daily", "date": "2026-03-02"},
            "embedding": [],
        },
        {
            "id": "chunk-2",
            "vault_rel_path": "Incidents/2026-03-02_freshness-gap.md",
            "heading_path": "Incidents/2026-03-02_freshness-gap.md#WhatHappened",
            "chunk_text": "Freshness gap detected on BTCUSDT and ETHUSDT.",
            "chunk_hash": "hash-2",
            "created_utc": "2026-03-02T10:00:00Z",
            "metadata": {"type": "incident", "date": "2026-03-02"},
            "embedding": [],
        },
    ]
    save_index_rows(
        db_dir,
        rows,
        provider_name="ollama",
        ollama_model="nomic-embed-text",
    )


def test_parse_args_supports_quoted_query() -> None:
    parsed = parse_args('query="freshness status" k=5')
    assert parsed == {"query": "freshness status", "k": "5"}


def test_run_rag_search_caps_k_and_returns_payload(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_index(repo)

    payload = run_rag_search(repo, {"query": "freshness status", "k": 999})

    assert payload["status"] == "OK"
    assert payload["provider"] == "lancedb"
    assert payload["db_path"] == "_local/lancedb/hongstr_obsidian.lancedb"
    assert 1 <= len(payload["chunks"]) <= 12
    assert payload["chunks"][0]["pointer"].startswith("Daily/2026/03/2026-03-02.md#")


def test_run_rag_search_warns_when_index_missing(tmp_path: Path) -> None:
    payload = run_rag_search(tmp_path, {"query": "freshness status"})

    assert payload["status"] == "WARN"
    assert payload["chunks"] == []
    assert "index_missing" in str(payload.get("warn", ""))
