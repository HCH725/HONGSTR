from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.obsidian_rag_lib import DB_PATH_REL, MAX_K, MAX_QUERY_CHARS, rag_search_from_repo


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ALLOWED_FILTERS = {"daily", "strategy", "incident"}


def _warn_payload(message: str) -> dict[str, Any]:
    return {
        "status": "WARN",
        "provider": "lancedb",
        "db_path": DB_PATH_REL,
        "chunks": [],
        "warn": message,
    }


def run_rag_search(repo: Path, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query", "") or "").strip()
    query = re.sub(r"\s+", " ", query)
    if len(query) > MAX_QUERY_CHARS:
        query = query[:MAX_QUERY_CHARS].rstrip()
    if not query:
        return _warn_payload("empty_query")

    try:
        k = int(args.get("k", 8))
    except Exception:
        k = 8
    k = max(1, min(k, MAX_K))

    filter_type_raw = str(args.get("filter_type", "") or "").strip().lower()
    filter_type = filter_type_raw or None
    if filter_type and filter_type not in _ALLOWED_FILTERS:
        return _warn_payload(f"invalid_filter_type: {filter_type}")

    since_date_raw = str(args.get("since_date", "") or "").strip()
    since_date = since_date_raw or None
    if since_date and not _DATE_RE.fullmatch(since_date):
        return _warn_payload("invalid_since_date")

    return rag_search_from_repo(
        repo,
        query=query,
        k=k,
        filter_type=filter_type,
        since_date=since_date,
    )
