#!/usr/bin/env python3
from __future__ import annotations

import argparse

from obsidian_common import compose_context
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
    if args.print_context:
        print(compose_context(rows), end="")
        return 0
    # Apply filter-type post-search (stable across LanceDB API versions)
    if args.filter_type:
        rows = [r for r in rows if r.get("type") == args.filter_type]

    for row in rows:
        print(
            f"{row.get('score', 0.0):.4f}\t"
            f"{row.get('heading_path', row.get('vault_rel_path', 'UNKNOWN'))}\t"
            f"{str(row.get('chunk_text', '')).replace(chr(10), ' ')[:200]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
