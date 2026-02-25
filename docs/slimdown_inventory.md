# HONGSTR Slim-down Inventory (SSOT Consolidation)

## Global Red Lines (Non-negotiables)
- stability-first: `src/hongstr/**` core diff=0
- ML/Research default `report_only`
- no committing generated artifacts under `data/**` (runtime state snapshots remain untracked)
- tg_cp strict read-only (`no subprocess`, `no os.system`, `no Popen`, no shell/auto-remediation)
- GitHub SSOT: commit + push + PR via `gh` + `scripts/gh_pr_merge.sh`
- Telegram-only unchanged

## 1) Current SSOT Producers (write `data/state/*.json`)

### Primary orchestrator
- [`scripts/refresh_state.sh`](/Users/hong/Projects/HONGSTR/scripts/refresh_state.sh)
  - Runs [`scripts/coverage_update.py`](/Users/hong/Projects/HONGSTR/scripts/coverage_update.py):28-29
  - Runs [`scripts/state_snapshots.py`](/Users/hong/Projects/HONGSTR/scripts/state_snapshots.py):46-47

### Canonical snapshot producer
- [`scripts/state_snapshots.py`](/Users/hong/Projects/HONGSTR/scripts/state_snapshots.py)
  - Writes `coverage_latest.json`:69
  - Writes `coverage_summary.json`:99
  - Writes `strategy_pool_summary.json`:129
  - Writes `regime_monitor_summary.json`:149-151
  - Writes `freshness_table.json`:209
  - Writes `execution_mode.json`:216
  - Writes `services_heartbeat.json`:254
  - Writes `coverage_matrix_latest.json`:325

### Other state writers (outside refresh pipeline)
- [`scripts/phase4_regime_monitor.py`](/Users/hong/Projects/HONGSTR/scripts/phase4_regime_monitor.py):168 writes `regime_monitor_latest.json`
- [`scripts/brake_healthcheck.py`](/Users/hong/Projects/HONGSTR/scripts/brake_healthcheck.py):117-119 writes `brake_health_latest.json`
- [`scripts/coverage_update.py`](/Users/hong/Projects/HONGSTR/scripts/coverage_update.py):16,103-105 writes `coverage_table.jsonl`
- [`scripts/semantics_check.py`](/Users/hong/Projects/HONGSTR/scripts/semantics_check.py):55-57 mutates `coverage_table.jsonl` (`NEEDS_REBASE`)

## 2) Canonical SSOT State Files (current)
- `data/state/freshness_table.json`
- `data/state/coverage_matrix_latest.json`
- `data/state/brake_health_latest.json`
- `data/state/regime_monitor_latest.json`
- `data/state/regime_monitor_summary.json`
- `data/state/execution_mode.json`
- `data/state/services_heartbeat.json`
- `data/state/coverage_summary.json`
- `data/state/coverage_latest.json`
- `data/state/strategy_pool_summary.json`
- `data/state/coverage_table.jsonl` (upstream table used for derived summaries)

## 3) Consumers (read-only) and what they read

### tg_cp
- [`_local/telegram_cp/tg_cp_server.py`](/Users/hong/Projects/HONGSTR/_local/telegram_cp/tg_cp_server.py)
- Reads:
  - `freshness_table.json`:363,644
  - `coverage_matrix_latest.json`:364,471,720
  - `brake_health_latest.json`:365,473,710,1098
  - `regime_monitor_latest.json`:366,474,707

### Dashboard API
- [`web/app/api/status/route.ts`](/Users/hong/Projects/HONGSTR/web/app/api/status/route.ts)
- Reads:
  - `execution_mode.json`:236
  - `services_heartbeat.json`:237
  - `coverage_matrix_latest.json`:398
  - `regime_monitor_summary.json`:424
  - `freshness_table.json`:435
  - fallback input `coverage_table.jsonl`:408

### Other scripts (consumer side)
- [`scripts/brake_healthcheck.py`](/Users/hong/Projects/HONGSTR/scripts/brake_healthcheck.py):17-18 consumes freshness/regime state to emit brake summary.

## 4) Duplicate status computations to remove (exact locations)

### tg_cp duplicates
- `_status_short_report()` recomputes status from raw rows/thresholds instead of consuming a single producer summary:
  - freshness status fold:508-522
  - coverage status and lag thresholds:523-553
  - brake status fold from results:555-560
  - regime monitor freshness status from mtime:572-578
  - SSOT roll-up:581-583
- `_collect_snapshot()` fallback recomputes freshness by scanning `data/derived/*` when snapshot absent:657-664
- `_collect_snapshot()` recomputes coverage aggregates from matrix rows:726-738
- `_snapshot_text()` recomputes freshness overall text state:774-801
- `skill_status_overview()` recomputes freshness/brake/coverage status classes:837-893

### Dashboard API duplicates
- `buildCoverageMatrix()` dynamic fallback recomputes totals by tailing/parsing `coverage_table.jsonl`:407-420
- `buildStrategyPool()` dynamic fallback recomputes leaderboard from raw `strategy_pool.json`:373-394

### Schema drift / status drift gaps discovered during inventory
- `execution_mode` timestamp key mismatch:
  - producer writes `last_updated_utc` ([`state_snapshots.py:214`](/Users/hong/Projects/HONGSTR/scripts/state_snapshots.py:214))
  - consumer reads `updated_at_utc` ([`route.ts:241`](/Users/hong/Projects/HONGSTR/web/app/api/status/route.ts:241))
- `router` expects `regime_monitor.status`, while primary state shape uses `overall`:
  - [`_local/telegram_cp/router.py:31`](/Users/hong/Projects/HONGSTR/_local/telegram_cp/router.py:31)

## 5) Gaps (what is still dynamic / fragmented)
- No single `system_health_latest.json`; each consumer still performs local roll-up logic.
- `refresh_state.sh` does not invoke `phase4_regime_monitor.py` or `brake_healthcheck.py`, so regime/brake can become stale relative to freshness/coverage snapshots.
- Dashboard still has dynamic fallback paths (`coverage_table.jsonl`, raw strategy pool) rather than strict SSOT-only reads.
- Some docs still reference outdated producers (for example `docs/brakes.md`, `docs/brakes_audit.md` mention `coverage_update.py` as freshness producer, while actual writer is `state_snapshots.py`).

## 6) Target Architecture (Slim-down)

### A) Single SSOT Producer boundary
- Keep `refresh_state.sh` as the only orchestrator entrypoint for state refresh.
- Move all status rollups/normalization into producer side; consumers only read `data/state/*.json` and render.

### B) Optional Health Pack aggregator
- Add one producer artifact: `data/state/system_health_latest.json` containing:
  - `ssot_status` (system health only)
  - `freshness`, `coverage_matrix`, `brake`, `regime_monitor`, `regime_signal`
  - `generated_utc` + source timestamps
- `/status` (tg_cp) and dashboard header should read this summary directly.

### C) launchd responsibility planes (single responsibility)
1. **Data Plane**: ETL / backfill / retention (`daily_etl`, `weekly_backfill`, `retention_cleanup`, `realtime_ws`)
2. **State Plane**: state refresh + aggregators (`refresh_state`, `phase4_regime_monitor`, `brake_healthcheck`, optional health pack)
3. **Control Plane**: read-only consumers (`tg_cp`, dashboard)

### D) Research convergence (spec-driven jobs)
- Keep research outputs `report_only` by default.
- Converge triggers to enqueue-only spec JSON; runner consumes specs without touching execution semantics.

## 7) Minimal follow-up refactor scope (PR-2)
- Replace tg_cp local status folding with direct read of producer summary (`system_health_latest.json` or equivalent consolidated state).
- Remove dashboard `coverage_table.jsonl` fallback path; rely on `coverage_matrix_latest.json` only.
- Align schema keys (`updated_at_utc` vs `last_updated_utc`, `overall` vs `status`) to eliminate adapter drift.
- Keep all changes outside `src/hongstr/**`.

## 8) Safety checklist
- [ ] `src/hongstr/**` unchanged
- [ ] no `data/**` staged/committed
- [ ] tg_cp no-exec guardrail unchanged
- [ ] docs-only PR merged with CI pass
