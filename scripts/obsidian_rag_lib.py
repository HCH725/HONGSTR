#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from obsidian_common import DEFAULT_LANCEDB_DIR, INDEX_MANIFEST_NAME, REPO_ROOT, load_index_rows
except ImportError:
    from scripts.obsidian_common import DEFAULT_LANCEDB_DIR, INDEX_MANIFEST_NAME, REPO_ROOT, load_index_rows


MAX_QUERY_CHARS = 512
MAX_K = 12
MAX_CHUNK_TEXT_CHARS = 1200
ALLOWED_FILTER_TYPES = {"daily", "strategy", "incident"}
DB_PATH_REL = DEFAULT_LANCEDB_DIR.relative_to(REPO_ROOT).as_posix()
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _base_payload(status: str) -> dict[str, Any]:
    return {
        "status": status,
        "provider": "lancedb",
        "db_path": DB_PATH_REL,
        "chunks": [],
    }


def _warn_payload(message: str) -> dict[str, Any]:
    payload = _base_payload("WARN")
    payload["warn"] = message
    return payload


def _normalize_query(query: str) -> str:
    text = re.sub(r"\s+", " ", str(query or "").strip())
    if len(text) > MAX_QUERY_CHARS:
        text = text[:MAX_QUERY_CHARS].rstrip()
    return text


def _normalize_k(value: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = 8
    return max(1, min(parsed, MAX_K))


def _normalize_filter_type(value: str | None) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text not in ALLOWED_FILTER_TYPES:
        raise ValueError(f"filter_type must be one of {sorted(ALLOWED_FILTER_TYPES)}")
    return text


def _normalize_since_date(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if not _DATE_RE.fullmatch(text):
        raise ValueError("since_date must match YYYY-MM-DD")
    return text


def _tokenize(text: str) -> list[str]:
    lowered = str(text or "").lower()
    tokens = _TOKEN_RE.findall(lowered)
    if tokens:
        return tokens
    compact = re.sub(r"\s+", " ", lowered).strip()
    return [compact] if compact else []


def _token_overlap(query_tokens: list[str], haystack: str) -> float:
    if not query_tokens:
        return 0.0
    haystack_tokens = set(_tokenize(haystack))
    if not haystack_tokens:
        return 0.0
    matches = sum(1 for token in query_tokens if token in haystack_tokens)
    return matches / len(query_tokens)


def _phrase_score(query_text: str, haystack: str) -> float:
    query_norm = str(query_text or "").lower().strip()
    haystack_norm = str(haystack or "").lower()
    if not query_norm or not haystack_norm:
        return 0.0
    return 1.0 if query_norm in haystack_norm else 0.0


def _metadata_text(metadata: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("type", "date", "strategy_id", "severity", "regime_slice", "ssot_ts_utc"):
        value = metadata.get(key)
        if value:
            parts.append(str(value))
    for key in ("symbols", "timeframes", "ssot_refs"):
        value = metadata.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value if item)
    return " ".join(parts)


def _row_matches_filters(
    row: dict[str, Any],
    filter_type: str | None,
    since_date: str | None,
) -> bool:
    metadata = row.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    if filter_type and metadata.get("type") != filter_type:
        return False
    if since_date:
        date_value = metadata.get("date")
        if isinstance(date_value, str) and date_value:
            return date_value >= since_date
        created_value = row.get("created_utc")
        if isinstance(created_value, str) and created_value:
            return created_value[:10] >= since_date
        return False
    return True


def _score_row(query_text: str, query_tokens: list[str], row: dict[str, Any]) -> float:
    heading = str(row.get("heading_path") or row.get("vault_rel_path") or "")
    chunk_text = str(row.get("chunk_text") or "")
    metadata = row.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    metadata_text = _metadata_text(metadata)

    heading_phrase = _phrase_score(query_text, heading)
    chunk_phrase = _phrase_score(query_text, chunk_text)
    metadata_phrase = _phrase_score(query_text, metadata_text)
    heading_overlap = _token_overlap(query_tokens, heading)
    chunk_overlap = _token_overlap(query_tokens, chunk_text)
    metadata_overlap = _token_overlap(query_tokens, metadata_text)

    return (
        (heading_phrase * 3.0)
        + (chunk_phrase * 2.0)
        + (metadata_phrase * 1.0)
        + (heading_overlap * 1.5)
        + (chunk_overlap * 2.5)
        + (metadata_overlap * 0.75)
    )


def _trim_chunk_text(text: str) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) <= MAX_CHUNK_TEXT_CHARS:
        return clean
    return clean[: MAX_CHUNK_TEXT_CHARS - 3].rstrip() + "..."


def _normalize_chunk(row: dict[str, Any], score: float) -> dict[str, Any]:
    metadata = row.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    vault_rel_path = str(row.get("vault_rel_path") or "UNKNOWN")
    heading_path = str(row.get("heading_path") or vault_rel_path)
    pointer = heading_path if "#" in heading_path else vault_rel_path
    return {
        "score": round(float(score), 4),
        "pointer": pointer,
        "vault_rel_path": vault_rel_path,
        "heading_path": heading_path,
        "text": _trim_chunk_text(str(row.get("chunk_text") or "")),
        "metadata": metadata,
    }


def rag_search_from_repo(
    repo_root: Path,
    query: str,
    k: int = 8,
    filter_type: str | None = None,
    since_date: str | None = None,
) -> dict[str, Any]:
    query_text = _normalize_query(query)
    if not query_text:
        return _warn_payload("empty_query")

    try:
        filter_name = _normalize_filter_type(filter_type)
        since_value = _normalize_since_date(since_date)
    except ValueError as exc:
        return _warn_payload(str(exc))

    safe_k = _normalize_k(k)
    db_dir = repo_root / DEFAULT_LANCEDB_DIR.relative_to(REPO_ROOT)
    manifest_path = db_dir / INDEX_MANIFEST_NAME
    if not manifest_path.exists():
        return _warn_payload(f"index_missing: {DB_PATH_REL}/{INDEX_MANIFEST_NAME}")

    try:
        rows = load_index_rows(db_dir)
    except Exception as exc:
        return _warn_payload(f"index_unreadable: {type(exc).__name__}")

    if not rows:
        return _warn_payload("index_unreadable_or_empty")

    query_tokens = _tokenize(query_text)
    chunks: list[dict[str, Any]] = []
    for row in rows:
        if not _row_matches_filters(row, filter_type=filter_name, since_date=since_value):
            continue
        score = _score_row(query_text, query_tokens, row)
        if score <= 0.0:
            continue
        chunks.append(_normalize_chunk(row, score))

    chunks.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    payload = _base_payload("OK")
    payload["chunks"] = chunks[:safe_k]
    if not payload["chunks"]:
        payload["warn"] = "no_matches"
    return payload


def rag_search(
    query: str,
    k: int = 8,
    filter_type: str | None = None,
    since_date: str | None = None,
) -> dict[str, Any]:
    return rag_search_from_repo(
        REPO_ROOT,
        query=query,
        k=k,
        filter_type=filter_type,
        since_date=since_date,
    )
