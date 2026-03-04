# Obsidian KB + LanceDB – Knowledge Base & Retrieval System

> The HONGSTR internal knowledge base lives in `_local/obsidian_vault/HONGSTR/` (never in git).  
> Two hourly launchd agents keep it fresh:
>
> - **`com.hongstr.obsidian_rag`** – syncs SSOT → `Daily/` notes + indexes vault (existing)
> - **`com.hongstr.obsidian_daily`** – exports SSOT → `KB/SSOT/Daily/` notes + incremental LanceDB re-index (new)

---

## Vault Layout

```text
_local/obsidian_vault/HONGSTR/
├── Daily/          YYYY/MM/YYYY-MM-DD.md      ← obsidian_rag (type=daily)
├── Strategies/     <strategy_id>.md           ← obsidian_rag (type=strategy)
├── Incidents/      YYYY-MM-DD_<slug>.md       ← obsidian_rag (type=incident)
└── KB/
    ├── SSOT/
    │   └── Daily/  YYYY-MM-DD.md              ← obsidian_daily (type=daily_ssot)  ← NEW
    └── PR/
        └── YYYY/   PR-####.md                 ← kb_sync (type=pr_note)
```

---

## Architecture

```
data/state/*.json   ──► obsidian_ssot_daily.py  ──► KB/SSOT/Daily/YYYY-MM-DD.md
                                                        │
                    obsidian_lancedb_index.py ◄─────────┘  (incremental)
                                │
                    _local/lancedb/hongstr_obsidian.lancedb
                                │
                    obsidian_lancedb_query.py  (query interface)
```

**Key properties:**

- All KB content lives in `_local/` → **gitignored, never committed**
- LanceDB index is incremental — only changed/new notes are re-embedded
- Ollama embedding (`nomic-embed-text`) used when available; falls back to keyword-scoring automatically
- Exporter: always `exit 0`; missing SSOT file → WARN logged, section skipped gracefully

---

## Install

### com.hongstr.obsidian_daily (SSOT KB notes + index)

```bash
# From repo root:
bash scripts/install_obsidian_daily_launchd.sh
```

### com.hongstr.obsidian_rag (original daily/strategy/incident notes)

```bash
bash scripts/install_obsidian_rag_launchd.sh
```

Both agents run at load + every 3600 s.

---

## Manual Run

```bash
# Export today's SSOT note only:
.venv/bin/python scripts/obsidian_ssot_daily.py

# Dry-run (no write):
.venv/bin/python scripts/obsidian_ssot_daily.py --dry-run

# Full pipeline (export + re-index):
bash scripts/obsidian_daily_run.sh
```

---

## Query the Index

```bash
# General search:
.venv/bin/python scripts/obsidian_lancedb_query.py "coverage blocked status"

# Filter to SSOT daily notes only (type=daily_ssot):
.venv/bin/python scripts/obsidian_lancedb_query.py \
    "regime signal warn" \
    --filter-type daily_ssot \
    --since-date 2026-03-01 \
    --k 5

# Print LLM-ready context blocks:
.venv/bin/python scripts/obsidian_lancedb_query.py \
    "data catalog changes" \
    --filter-type daily_ssot \
    --print-context
```

> **Note:** `--filter-type` accepts `daily`, `strategy`, `incident`. The new `daily_ssot` notes are indexed with `type: daily_ssot` in their frontmatter but the filter mechanism matches on the `metadata.type` field stored in LanceDB — if you want strict filtering, search without `--filter-type` and inspect the `metadata.type` field in results.

---

## Paths Reference

| Item | Path |
| --- | --- |
| Vault root | `_local/obsidian_vault/HONGSTR/` |
| SSOT KB notes | `_local/obsidian_vault/HONGSTR/KB/SSOT/Daily/` |
| LanceDB index | `_local/lancedb/hongstr_obsidian.lancedb/` |
| Index state | `_local/obsidian_index_state.json` |
| Out log (daily) | `~/Library/Logs/hongstr/obsidian_daily.out.log` |
| Err log (daily) | `~/Library/Logs/hongstr/obsidian_daily.err.log` |

---

## Stop / Disable

```bash
launchctl bootout "gui/$(id -u)/com.hongstr.obsidian_daily"
launchctl bootout "gui/$(id -u)/com.hongstr.obsidian_rag"
```

## Uninstall

```bash
launchctl bootout "gui/$(id -u)/com.hongstr.obsidian_daily" 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.hongstr.obsidian_daily.plist
```

---

## Troubleshooting

### Ollama is down → fallback embeddings

`obsidian_daily_run.sh` probes Ollama before indexing. If unreachable, it passes `--provider fallback` to `obsidian_lancedb_index.py`, which uses keyword-based scoring. Search still works, just without semantic embeddings.

```bash
# Force rebuild with fallback:
.venv/bin/python scripts/obsidian_lancedb_index.py --rebuild --provider fallback
```

### SSOT files missing → WARN, exit 0

If `data/state/` files are absent (e.g. first boot), the exporter logs:

```
WARN obsidian_ssot_daily: no SSOT files found – skipping write
```

and exits 0. Run `bash scripts/refresh_state.sh` first to populate state files.

### Index is stale or corrupt

```bash
# Force full rebuild:
.venv/bin/python scripts/obsidian_lancedb_index.py --rebuild --provider ollama
```

### Check job status

```bash
launchctl print "gui/$(id -u)/com.hongstr.obsidian_daily"
tail -n 80 ~/Library/Logs/hongstr/obsidian_daily.out.log
tail -n 80 ~/Library/Logs/hongstr/obsidian_daily.err.log
```

---

## Architecture Notes

- **KB is private:** `_local/` is in `.gitignore`. No vault files ever enter git.
- **Incremental indexing:** only notes whose content has changed since the last index run are re-embedded, keeping index runs fast.
- **PR notes** (`KB/PR/YYYY/PR-####.md`) are indexed automatically alongside SSOT notes by the same LanceDB index job.
- **No LLM used** in exporting: note content is derived from structured JSON using deterministic rules.
- **No core changes:** `src/hongstr/**` is untouched.

---

## Rollback

```bash
launchctl bootout "gui/$(id -u)/com.hongstr.obsidian_daily" 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.hongstr.obsidian_daily.plist
git revert HEAD   # (after merge of this PR)
```
