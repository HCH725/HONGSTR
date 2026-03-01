#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from obsidian_common import (
    DEFAULT_LANCEDB_DIR,
    DEFAULT_STATE_FILE,
    DEFAULT_VAULT_ROOT,
    REPO_ROOT,
    FallbackEmbeddingProvider,
    build_note_chunks,
    load_index_rows,
    load_sync_state,
    make_embedding_provider,
    maybe_clear_index,
    now_utc_iso,
    save_index_rows,
    save_sync_state,
    text_hash,
)


def _coerce_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = (
        "type",
        "date",
        "strategy_id",
        "severity",
        "regime_slice",
        "symbols",
        "timeframes",
        "ssot_refs",
        "ssot_ts_utc",
    )
    payload = {key: metadata.get(key) for key in allowed_keys if key in metadata}
    payload.setdefault("type", metadata.get("type", "unknown"))
    return payload


def index_obsidian_vault(
    repo_root: Path = REPO_ROOT,
    rebuild: bool = False,
    provider_name: str = "ollama",
    ollama_model: str | None = None,
) -> dict[str, Any]:
    vault_root = repo_root / DEFAULT_VAULT_ROOT.relative_to(REPO_ROOT)
    db_dir = repo_root / DEFAULT_LANCEDB_DIR.relative_to(REPO_ROOT)
    state_path = repo_root / DEFAULT_STATE_FILE.relative_to(REPO_ROOT)
    state = load_sync_state(state_path)
    prior_index = state.get("index", {})
    prior_provider = prior_index.get("provider")
    prior_model = prior_index.get("ollama_model")
    provider_changed = bool(
        not rebuild and prior_provider and (prior_provider != provider_name or prior_model != ollama_model)
    )

    if rebuild or provider_changed:
        maybe_clear_index(db_dir)
        existing_rows: list[dict[str, Any]] = []
    else:
        existing_rows = load_index_rows(db_dir)

    existing_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    existing_by_chunk_hash: dict[str, dict[str, Any]] = {}
    for row in existing_rows:
        existing_by_path[str(row.get("vault_rel_path", ""))].append(row)
        chunk_hash = row.get("chunk_hash")
        if isinstance(chunk_hash, str) and chunk_hash and chunk_hash not in existing_by_chunk_hash:
            existing_by_chunk_hash[chunk_hash] = row

    note_files = sorted(vault_root.rglob("*.md")) if vault_root.exists() else []
    if not note_files:
        if rebuild or provider_changed:
            save_index_rows(db_dir, [], provider_name, ollama_model)
            state["index"] = {"provider": provider_name, "ollama_model": ollama_model, "files": {}}
            save_sync_state(state_path, state, dry_run=False)
        return {"rows": 0, "changed_files": 0, "warnings": ["WARN: no Markdown notes found in vault."]}

    provider = make_embedding_provider(provider_name, ollama_model)
    current_now = now_utc_iso()
    new_rows: list[dict[str, Any]] = []
    new_file_state: dict[str, Any] = {}
    pending_texts_by_hash: dict[str, str] = {}
    pending_hash_order: list[str] = []
    unresolved_rows: list[dict[str, Any]] = []
    changed_files = 0

    for note_file in note_files:
        rel_path = note_file.relative_to(vault_root).as_posix()
        note_text = note_file.read_text(encoding="utf-8")
        file_hash = text_hash(note_text)
        prior_file_state = {} if provider_changed else prior_index.get("files", {}).get(rel_path, {})
        if not rebuild and prior_file_state.get("file_hash") == file_hash:
            rows_for_path = sorted(
                existing_by_path.get(rel_path, []), key=lambda item: str(item.get("id", ""))
            )
            new_rows.extend(rows_for_path)
            new_file_state[rel_path] = {
                "file_hash": file_hash,
                "chunk_ids": [row.get("id") for row in rows_for_path],
                "indexed_utc": prior_file_state.get("indexed_utc", current_now),
            }
            continue

        changed_files += 1
        rows_for_file: list[dict[str, Any]] = []
        for chunk in build_note_chunks(rel_path, note_text):
            existing_chunk = existing_by_chunk_hash.get(chunk.chunk_hash)
            row = {
                "id": chunk.metadata.get("id"),
                "vault_rel_path": rel_path,
                "heading_path": chunk.heading_path,
                "chunk_text": chunk.chunk_text,
                "chunk_hash": chunk.chunk_hash,
                "created_utc": (
                    existing_chunk.get("created_utc", current_now) if existing_chunk else current_now
                ),
                "metadata": _coerce_metadata(chunk.metadata),
                "embedding": existing_chunk.get("embedding") if existing_chunk else None,
            }
            rows_for_file.append(row)
            if row["embedding"] is None:
                if chunk.chunk_hash not in pending_texts_by_hash:
                    pending_hash_order.append(chunk.chunk_hash)
                    pending_texts_by_hash[chunk.chunk_hash] = chunk.chunk_text
                unresolved_rows.append(row)
        rows_for_file.sort(key=lambda item: str(item["id"]))
        new_rows.extend(rows_for_file)
        new_file_state[rel_path] = {
            "file_hash": file_hash,
            "chunk_ids": [row["id"] for row in rows_for_file],
            "indexed_utc": current_now,
        }

    if pending_hash_order:
        pending_vectors: list[list[float]] | None = None
        try:
            pending_vectors = provider.embed_texts([pending_texts_by_hash[key] for key in pending_hash_order])
        except Exception:
            if provider_name == "ollama":
                provider = FallbackEmbeddingProvider()
                provider_name = provider.name
                pending_vectors = provider.embed_texts(
                    [pending_texts_by_hash[key] for key in pending_hash_order]
                )
            else:
                raise
        vectors_by_hash = dict(zip(pending_hash_order, pending_vectors))
        for row in unresolved_rows:
            row["embedding"] = vectors_by_hash[row["chunk_hash"]]

    new_rows.sort(key=lambda item: str(item["id"]))
    save_index_rows(db_dir, new_rows, provider_name, ollama_model)
    state["index"] = {
        "provider": provider_name,
        "ollama_model": ollama_model,
        "files": new_file_state,
        "indexed_utc": current_now,
    }
    save_sync_state(state_path, state, dry_run=False)
    return {"rows": len(new_rows), "changed_files": changed_files, "warnings": []}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index Obsidian vault notes into local LanceDB-compatible storage.")
    parser.add_argument("--rebuild", action="store_true", help="Drop and recreate the local index manifest.")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Accepted for compatibility; incremental is the default behavior.",
    )
    parser.add_argument(
        "--provider",
        choices=("ollama", "fallback"),
        default="ollama",
        help="Embedding provider to use.",
    )
    parser.add_argument(
        "--ollama-model",
        default=None,
        help="Optional Ollama embedding model name.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = index_obsidian_vault(
        rebuild=args.rebuild,
        provider_name=args.provider,
        ollama_model=args.ollama_model,
    )
    for warning in result.get("warnings", []):
        print(warning)
    print(
        f"obsidian_lancedb_index: rows={result.get('rows', 0)} "
        f"changed_files={result.get('changed_files', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
