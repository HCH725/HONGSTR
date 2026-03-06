# Obsidian / LanceDB SOP Appendix v1

Last updated: 2026-03-06 (UTC+8)  
Status: governance appendix (docs-only), non-core, no runtime path mutation.

## 0. Purpose

Define sidecar knowledge operations for Obsidian and LanceDB without violating HONGSTR baseline:

- SSOT remains `data/state/*`
- Obsidian is human-readable governance memory
- LanceDB is retrieval index, not authoritative state

## 1. Data Residency Rules

## 1.1 SSOT-only (must never be replaced)

These must remain canonical only in state plane outputs:

- `data/state/system_health_latest.json`
- `data/state/daily_report_latest.json`
- `data/state/services_heartbeat.json`
- `data/state/coverage_matrix_latest.json`
- `data/state/brake_health_latest.json`
- any `/status` or `/daily` status-class source files

Rationale:

- deterministic state publication
- single writer ownership
- direct consumption by tg_cp/dashboard

## 1.2 Dual-write to Obsidian (human-facing summaries)

Allowed dual-write content:

- daily status digest (Markdown summary with SSOT pointers)
- incident stubs/postmortems
- strategy summary cards
- decision/runbook/review records

Source and sinks:

- source: SSOT files + selected research report outputs
- sink: `_local/obsidian_vault/HONGSTR/*`

Required rule:

- every note must include back-pointer to SSOT/report path and timestamp

## 1.3 LanceDB ingestion scope (summary/chunk index only)

Allowed:

- note chunks + metadata + pointers
- incident/report/skill context retrieval fields

Not allowed:

- raw SSOT JSON replacement copy used as control-plane truth
- raw large artifacts (parquet/pkl/db dumps) into index

Current implementation anchor:

- `_local/lancedb/hongstr_obsidian.lancedb/chunks.json`
- optional native table `obsidian_chunks` via `lancedb` package

## 2. Recommended Obsidian Vault Structure

Recommended governance folders:

```text
_local/obsidian_vault/HONGSTR/
  Agents/
  Incidents/
  Reports/
  Skills/
  Dashboards/
  KB/
  Decisions/
  Runbooks/
  Reviews/
```

Current baseline compatibility:

- existing auto-generated paths:
  - `Daily/`
  - `Strategies/`
  - `Incidents/`
- existing mirror whitelist:
  - `KB/`
  - `Dashboards/`

SOP:

- keep current producers unchanged
- add new governance folders incrementally
- expand mirror whitelist only after operator approval

## 3. Recommended LanceDB Collections (Logical)

To keep backward compatibility with existing single-manifest index, define logical collections in metadata first:

- `agent_events`
- `incident_memory`
- `research_reports`
- `skills_registry`

Implementation note:

- do not split physical storage in P0 path now
- use metadata field (for example `collection`) under existing chunk rows
- future physical separation can be done in non-P0 migration PR

## 4. Exporter vs Indexer Responsibility Boundary

## 4.1 Exporter responsibilities

Exporter examples:

- `scripts/obsidian_sync.py`
- `scripts/obsidian_dashboards_export.sh`
- `scripts/kb_sync_github_prs.py`

Exporter rules:

- read from SSOT/reports
- write Markdown only to `_local/obsidian_vault/*`
- never write canonical `data/state/*`
- never run trading/execution paths

## 4.2 Indexer responsibilities

Indexer examples:

- `scripts/obsidian_lancedb_index.py`
- `scripts/obsidian_rag_run.sh`
- `scripts/obsidian_lancedb_query.py`

Indexer rules:

- read Obsidian notes
- write index artifacts only under `_local/lancedb/*` and `_local/obsidian_index_state.json`
- provide retrieval context only
- never back-write SSOT status fields

## 5. Why Obsidian/LanceDB Cannot Become `/status` or `/daily` Truth

Reason-1: Asynchronous lag

- export/index schedule is decoupled from state refresh cadence

Reason-2: Lossy representation

- notes/chunks are summarized views with truncation and semantic transformation

Reason-3: Non-deterministic retrieval

- top-K recall order and provider fallback may vary

Reason-4: Sidecar failure tolerance

- mirror/index jobs are intentionally non-blocking (`WARN`, `exit 0`)

Therefore:

- `/status` and `/daily` must continue to read direct SSOT files only
- Obsidian/LanceDB output can enrich operator context, not replace health truth

## 6. iCloud Mirror SOP (Governance Visibility)

Current pipeline:

- `scripts/obsidian_mirror_run.sh` (export -> mirror)
- `scripts/obsidian_mirror_publish.sh` (rsync to iCloud vault)

Current target:

- `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/HONGSTR_MIRROR/`

Current publish scope:

- `KB/**`
- `Dashboards/**`

Safety rules already enforced:

- no delete mode
- no raw/state/cache/db sync
- no parquet/pkl/pickle/joblib sync
- lock-protected, warn-only on failure

## 7. Degrade / Kill Switch / Removal SOP

## 7.1 Degrade mode

- keep mirror pipeline non-blocking:
  - exporter failure should not block mirror run
  - mirror failure should not block core jobs
- keep rag provider fallback:
  - ollama unavailable -> fallback embeddings

## 7.2 Kill switch

- disable mirror one-shot:
  - `MIRROR_ENABLED=0 bash scripts/obsidian_mirror_publish.sh`
- skip dashboard export:
  - `DASHBOARDS_EXPORT_ENABLED=0 bash scripts/obsidian_mirror_run.sh`
- strict-stop rag failures (optional):
  - `OBSIDIAN_RAG_STRICT=1`
- unload launchd jobs when needed:
  - `com.hongstr.obsidian_mirror`
  - `com.hongstr.obsidian_rag`
  - `com.hongstr.kb_sync`

## 7.3 Removal plan

- Step 1: disable sidecar launchd labels
- Step 2: preserve `_local` artifacts for audit window
- Step 3: rollback by PR revert if rollout introduced drift
- Step 4: keep baseline-only stack (`refresh_state`, `tg_cp`, `dashboard`)

## 8. Quick Compliance Checklist

- [ ] SSOT writer remains single owner (`state_snapshots.py`)
- [ ] tg_cp/dashboard status paths still read SSOT directly
- [ ] Obsidian exporter writes only markdown sidecar artifacts
- [ ] LanceDB indexer writes only `_local/lancedb/*`
- [ ] iCloud mirror remains whitelist-only and non-destructive
- [ ] no `data/**`, `_local/**`, parquet/pkl/lancedb artifacts are committed
