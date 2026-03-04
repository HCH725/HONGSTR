#!/usr/bin/env python3
from __future__ import annotations

import argparse

from obsidian_common import DEFAULT_LANCEDB_DIR, compose_context, load_index_rows
from obsidian_rag_lib import rag_search


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the local Obsidian note vector index.")
    parser.add_argument("query", help="Natural-language query.")
    parser.add_argument("--k", type=int, default=10, help="Maximum number of chunks to return.")
    parser.add_argument(
        "--filter-type",
        choices=("daily","daily_ssot","strategy","incident"),
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


def _fallback_text_search(query: str, k: int) -> list[dict[str, object]]:
    query_norm = str(query or "").strip().lower()
    if not query_norm:
        return []

    try:
        source_rows = load_index_rows(DEFAULT_LANCEDB_DIR)
    except Exception:
        return []

    hits: list[dict[str, object]] = []
    max_hits = max(int(k), 50)
    for row in source_rows:
        heading_path = str(row.get("heading_path") or row.get("vault_rel_path") or "UNKNOWN")
        vault_rel_path = str(row.get("vault_rel_path") or "UNKNOWN")
        chunk_text = str(row.get("chunk_text") or "")
        haystack = f"{heading_path}\n{vault_rel_path}\n{chunk_text}".lower()
        if query_norm not in haystack:
            continue

        metadata = row.get("metadata")
        hits.append(
            {
                "score": 0.0,
                "heading_path": heading_path,
                "vault_rel_path": vault_rel_path,
                "chunk_text": chunk_text,
                "metadata": metadata if isinstance(metadata, dict) else {},
            }
        )
        if len(hits) >= max_hits:
            break
    return hits


def main() -> int:
    args = parse_args()
    payload = rag_search(
        query=args.query,
        k=args.k,
        filter_type=args.filter_type,
        since_date=args.since_date,
    )
    rows = []
    for chunk in payload.get("chunks", []):
        if not isinstance(chunk, dict):
            continue
        rows.append(
            {
                "score": chunk.get("score", 0.0),
                "heading_path": chunk.get("heading_path", chunk.get("pointer", "UNKNOWN")),
                "vault_rel_path": chunk.get("vault_rel_path", "UNKNOWN"),
                "chunk_text": chunk.get("text", ""),
                "metadata": chunk.get("metadata", {}),
            }
        )

    # HONGSTR_FALLBACK_TEXTSEARCH_V1: deterministic fallback when vector search returns 0
    if not rows:
        rows = _fallback_text_search(args.query, args.k)

    if args.print_context:
        print(compose_context(rows), end="")
        return 0
    # Apply filter-type post-search (stable across LanceDB API versions)
    if args.filter_type:
        # HONGSTR_FILTER_BY_POINTER_V1
        def _ptr(r: dict[str, object]) -> str:
            return str(
                r.get("pointer")
                or r.get("vault_rel_path")
                or r.get("heading_path")
                or r.get("path")
                or r.get("source_path")
                or ""
            )
        ft = args.filter_type
        if ft == "daily_ssot":
            rows = [r for r in rows if _ptr(r).startswith("KB/SSOT/Daily/")]
        elif ft == "daily":
            rows = [r for r in rows if _ptr(r).startswith("Daily/")]
        elif ft == "incident":
            rows = [r for r in rows if _ptr(r).startswith("Incidents/")]
        elif ft == "strategy":
            rows = [r for r in rows if _ptr(r).startswith("Strategies/") or _ptr(r).startswith("StrategyCards/")]


    for row in rows:
        print(
            f"{row.get('score', 0.0):.4f}\t"
            f"{row.get('heading_path', row.get('vault_rel_path', 'UNKNOWN'))}\t"
            f"{str(row.get('chunk_text', '')).replace(chr(10), ' ')[:200]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
