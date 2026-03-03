# Obsidian + LanceDB Research Notebook

## Overview

This adds a local, PR-safe research notebook pipeline:

1. `data/state/*.json` remains the single source of truth (read-only).
2. `scripts/obsidian_sync.py` renders human-readable Markdown notes into a local Obsidian-style vault under `_local/obsidian_vault/HONGSTR/`.
3. `scripts/obsidian_lancedb_index.py` chunks those notes and builds a local vector index under `_local/lancedb/hongstr_obsidian.lancedb/`.
4. `scripts/obsidian_lancedb_query.py` retrieves top-K chunks for RAG or manual review.

The local notebook is for operator research context only. It does not change trading, ETL, backtest, or control-plane execution semantics.

## Storage Model

### SSOT

- Source: `data/state/`
- Ownership: existing state-plane writers
- Contents: canonical JSON snapshots

### Obsidian Vault

- Root: `_local/obsidian_vault/HONGSTR/`
- Contents: Markdown notes only
- Notes link back to SSOT via relative pointers such as `data/state/daily_report_latest.json`
- Notes include `generated_utc` and `ssot_ts_utc`

### LanceDB-Compatible Index

- Root: `_local/lancedb/hongstr_obsidian.lancedb/`
- Primary stored artifact: `chunks.json` manifest with chunk metadata, embeddings, and note pointers
- If the optional `lancedb` Python package is installed locally, the script also mirrors rows into a native LanceDB table in the same directory
- The index stores chunk snippets plus metadata and pointers, not raw SSOT JSON

### Incremental State

- State file: `_local/obsidian_index_state.json`
- Tracks note hashes and index file hashes for idempotent incremental updates

## Safety Rules

- `src/hongstr/` is untouched.
- No new execution capability is added to `tg_cp`.
- `_local/**` remains local-only and must not be committed.
- Raw klines, parquet, and large data artifacts are not copied into notes or the vector index.
- All changes continue through normal PR review.

## Commands

### Phase 0: Sync notes

Dry-run:

```bash
.venv/bin/python scripts/obsidian_sync.py --dry-run
```

Write notes:

```bash
.venv/bin/python scripts/obsidian_sync.py
```

Optional flags:

- `--now-utc 2026-03-02T10:00:00Z`
- `--write-strategies on|off`
- `--write-incidents on|off`
- `--dry-run`

### Phase 1: Build the index

Rebuild with deterministic fallback embeddings:

```bash
.venv/bin/python scripts/obsidian_lancedb_index.py --provider fallback --rebuild
```

Incremental with local Ollama embeddings:

```bash
.venv/bin/python scripts/obsidian_lancedb_index.py --provider ollama --ollama-model nomic-embed-text
```

If Ollama is unavailable and `--provider ollama` is requested, the indexer falls back to deterministic local embeddings so the pipeline remains usable for tests and smoke checks.

### Query

```bash
.venv/bin/python scripts/obsidian_lancedb_query.py "why coverage blocked" --k 5 --print-context
```

Useful filters:

- `--filter-type daily`
- `--filter-type strategy`
- `--filter-type incident`
- `--since-date 2026-03-01`

## Note Templates

### Daily Research Note

- Path: `Daily/YYYY/MM/YYYY-MM-DD.md`
- Sections: `Summary`, `SystemHealth`, `DataQuality`, `Coverage`, `RegimeSignal`, `StrategyTop`, `ActionsNext`

### Strategy Card

- Path: `Strategies/<strategy_id>.md`
- Incremental updates use a stable `evidence_hash`

### Incident Card

- Path: `Incidents/<YYYY-MM-DD>_<slug>.md`
- Generated deterministically from WARN/FAIL conditions in system health, coverage, or brake health

## Testing

```bash
bash scripts/guardrail_check.sh
.venv/bin/python -m pytest tests/test_obsidian_rag.py
```

## Hourly launchd Schedule

Install or reload the user LaunchAgent:

```bash
bash scripts/install_obsidian_rag_launchd.sh
```

Force a run immediately:

```bash
launchctl kickstart -k gui/$(id -u)/com.hongstr.obsidian_rag
```

Stop and unload the job:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hongstr.obsidian_rag.plist
```

Logs live at:

- `~/Library/Logs/hongstr/obsidian_rag.out.log`
- `~/Library/Logs/hongstr/obsidian_rag.err.log`

Provider auto-select:

- `scripts/obsidian_rag_run.sh` probes `http://127.0.0.1:11434/api/embeddings` with model `nomic-embed-text`.
- If the probe succeeds, the hourly run uses `--provider ollama --ollama-model nomic-embed-text`.
- If the probe fails, the run automatically falls back to `--provider fallback`.

Safety:

- Failures are warn-only by default: the wrapper prints a `WARN` line and exits `0`, so the hourly schedule stays non-blocking.
- Notes, index state, and lock state stay local-only: the sync/index scripts write under `_local/**`, and the overlap lock lives under `/tmp/`.
- The tracked plist is a template with placeholders; the installer renders absolute paths only into `~/Library/LaunchAgents/`.

## Operational Notes

- The query path reads from the local index manifest and computes similarity locally.
- Chunking is deterministic: headings first, then fixed-size chunk windows with overlap.
- The system is designed for repeated daily runs without rewriting unchanged notes or re-embedding unchanged chunks.
