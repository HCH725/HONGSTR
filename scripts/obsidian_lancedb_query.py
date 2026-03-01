#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from obsidian_common import (
    DEFAULT_LANCEDB_DIR,
    DEFAULT_STATE_FILE,
    REPO_ROOT,
    FallbackEmbeddingProvider,
    compose_context,
    cosine_similarity,
    load_index_rows,
    load_sync_state,
    make_embedding_provider,
)


def _token_overlap_score(query_text: str, chunk_text: str) -> float:
    query_tokens = set(query_text.lower().split())
    chunk_tokens = set(chunk_text.lower().split())
    if not query_tokens or not chunk_tokens:
        return 0.0
    return len(query_tokens & chunk_tokens) / len(query_tokens)


def _row_matches_filters(
    row: dict[str, Any],
    filter_type: str | None,
    since_date: str | None,
) -> bool:
    metadata = row.get("metadata", {})
    if filter_type and metadata.get("type") != filter_type:
        return False
    if since_date:
        date_value = metadata.get("date")
        if isinstance(date_value, str):
            return date_value >= since_date
        created_value = row.get("created_utc")
        if isinstance(created_value, str) and created_value[:10] >= since_date:
            return True
        return False
    return True


def query_index(
    query_text: str,
    repo_root: Path = REPO_ROOT,
    k: int = 10,
    filter_type: str | None = None,
    since_date: str | None = None,
) -> list[dict[str, Any]]:
    db_dir = repo_root / DEFAULT_LANCEDB_DIR.relative_to(REPO_ROOT)
    state_path = repo_root / DEFAULT_STATE_FILE.relative_to(REPO_ROOT)
    state = load_sync_state(state_path)
    rows = load_index_rows(db_dir)
    if not rows:
        return []

    filtered_rows = [
        row for row in rows if _row_matches_filters(row, filter_type=filter_type, since_date=since_date)
    ]
    if not filtered_rows:
        return []

    provider_name = state.get("index", {}).get("provider", "fallback")
    ollama_model = state.get("index", {}).get("ollama_model")
    first_embedding = filtered_rows[0].get("embedding") or []
    try:
        provider = make_embedding_provider(provider_name, ollama_model)
        query_vector = provider.embed_texts([query_text])[0]
    except Exception:
        provider = FallbackEmbeddingProvider(dimension=max(1, len(first_embedding) or 64))
        query_vector = provider.embed_texts([query_text])[0]

    scored_rows = []
    for row in filtered_rows:
        embedding = row.get("embedding") or []
        content_overlap = _token_overlap_score(query_text, str(row.get("chunk_text", "")))
        heading_overlap = _token_overlap_score(query_text, str(row.get("heading_path", "")))
        semantic_score = cosine_similarity(query_vector, embedding)
        if provider_name == "fallback":
            score = (content_overlap * 2.0) + (heading_overlap * 0.5) + (semantic_score * 0.1)
        else:
            score = semantic_score + (0.25 * content_overlap)
        if score < -0.5:
            continue
        enriched = dict(row)
        enriched["score"] = score
        scored_rows.append(enriched)
    scored_rows.sort(key=lambda item: float(item.get("score", -1.0)), reverse=True)
    return scored_rows[:k]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the local Obsidian note vector index.")
    parser.add_argument("query", help="Natural-language query.")
    parser.add_argument("--k", type=int, default=10, help="Maximum number of chunks to return.")
    parser.add_argument(
        "--filter-type",
        choices=("daily", "strategy", "incident"),
        default=None,
        help="Optional note type filter.",
    )
    parser.add_argument(
        "--since-date",
        default=None,
        help="Optional YYYY-MM-DD lower bound for daily/created dates.",
    )
    parser.add_argument(
        "--print-context",
        action="store_true",
        help="Print formatted context blocks suitable for LLM use.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = query_index(
        query_text=args.query,
        k=args.k,
        filter_type=args.filter_type,
        since_date=args.since_date,
    )
    if args.print_context:
        print(compose_context(rows), end="")
        return 0
    for row in rows:
        print(
            f"{row.get('score', 0.0):.4f}\t"
            f"{row.get('heading_path', row.get('vault_rel_path', 'UNKNOWN'))}\t"
            f"{str(row.get('chunk_text', '')).replace(chr(10), ' ')[:200]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
