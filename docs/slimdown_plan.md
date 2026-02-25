# HONGSTR Slimdown Plan (Phase 3)

Last updated (UTC): 2026-02-25  
Scan evidence: `reports/slimdown_scan_2026-02-25T151736Z.log`

## 1) Current SSOT Producers and Writers

### Primary orchestrator
- `scripts/refresh_state.sh`
  - updates coverage table: `scripts/refresh_state.sh:28-30`
  - generates snapshots: `scripts/refresh_state.sh:46-47`

### Canonical state snapshot writer
- `scripts/state_snapshots.py`
  - writes `coverage_latest.json`: `scripts/state_snapshots.py:122`
  - writes `coverage_summary.json`: `scripts/state_snapshots.py:152`
  - writes `strategy_pool_summary.json`: `scripts/state_snapshots.py:182`
  - writes `regime_monitor_summary.json`: `scripts/state_snapshots.py:202-204`
  - writes `freshness_table.json`: `scripts/state_snapshots.py:262`
  - writes `execution_mode.json`: `scripts/state_snapshots.py:269`
  - writes `services_heartbeat.json`: `scripts/state_snapshots.py:307`
  - writes `coverage_matrix_latest.json`: `scripts/state_snapshots.py:378`
  - writes `system_health_latest.json`: `scripts/state_snapshots.py:534`

### Other writers (still active)
- `scripts/coverage_update.py` writes `coverage_table.jsonl`: `scripts/coverage_update.py:16`, `scripts/coverage_update.py:103-105`
- `scripts/semantics_check.py` mutates `coverage_table.jsonl` status: `scripts/semantics_check.py:13`, `scripts/semantics_check.py:55-57`
- `scripts/phase4_regime_monitor.py` writes `regime_monitor_latest.json`: `scripts/phase4_regime_monitor.py:168-169`
- `scripts/brake_healthcheck.py` writes `brake_health_latest.json`: `scripts/brake_healthcheck.py:17-19`, `scripts/brake_healthcheck.py:115-119`

## 2) Consumer-side Secondary Computations (Grouped)

### tg_cp (`_local/telegram_cp/tg_cp_server.py`)
- `/status` fallback path still does local fold/aggregation if health pack missing:
  - fallback entry: `tg_cp_server.py:574-580`
  - component parsing + missing/unreadable handling: `tg_cp_server.py:582-641`
  - freshness/coverage/brake/regime local status fold: `tg_cp_server.py:643-735`
- `_collect_snapshot()` still computes control-plane status from logs/reports for LLM context:
  - dashboard log tail health: `tg_cp_server.py:777-779`
  - ETL tail-derived status: `tg_cp_server.py:836-838`
  - coverage local aggregation: `tg_cp_server.py:855-899`

### dashboard API (`web/app/api/status/route.ts`)
- status endpoint still mixes SSOT and non-SSOT sources:
  - `buildCoverageSummary()` reads reports + csv parse: `route.ts:312-343`
  - `buildTimeline()` tails execution jsonl streams: `route.ts:345-364`
  - `listBacktestRuns()` scans backtest filesystem: `route.ts:405-462`
  - selection fallback to global artifact: `route.ts:485-488`
- schema drift / warning drift:
  - warning points to old path for strategy pool: `route.ts:507`
  - services parse expects array only, while producer writes map: `route.ts:248-257` vs `state_snapshots.py:280-305`

### scripts (state-adjacent)
- `phase4_regime_monitor.py` uses `fallback_fragment` when no full run: `scripts/phase4_regime_monitor.py:37-40`
- `brake_healthcheck.py` has helper script subprocess + manual scan fallback: `scripts/brake_healthcheck.py:35-46`
- `state_snapshots.py` freshness producer derives ages directly from `data/derived/*`: `scripts/state_snapshots.py:214-243`

## 3) What to Delete/Replace Next (Minimal Diffs)

### Immediate (safe, small)
1. `web/app/api/status/route.ts`
   - fix service heartbeat parsing to accept producer map format (`services: {name -> payload}`) in addition to array.
   - update stale warning text from `data/state/strategy_pool.json` to `data/state/strategy_pool_summary.json`.
2. `scripts/state_snapshots.py`
   - normalize unknown `regime_monitor_summary` timestamp field to `updated_utc` (currently writes `last_updated_utc` on missing source).

### Keep for now (documented debt, avoid risky scope)
1. `tg_cp_server.py` `/status` fallback computation (`:582-735`)
   - keep as resilience path if `system_health_latest.json` is missing/unreadable.
2. `route.ts` backtest/timeline scans (`:345-462`)
   - keep because dashboard currently presents detailed run/timeline views that are not yet represented in a compact SSOT snapshot.
3. `brake_healthcheck.py` subprocess/manual scan (`:35-46`)
   - keep until a dedicated producer pipeline for backtest artifact health is introduced.

## 4) PR Plan

### PR1 (docs-only)
- Add this document (`docs/slimdown_plan.md`).
- Include fresh scan evidence and exact code refs.
- No behavior change.

### PR2 (minimal consumer refactor)
- `web/app/api/status/route.ts`
  - heartbeat map parsing support
  - strategy pool warning path fix
- `scripts/state_snapshots.py`
  - `regime_monitor_summary` unknown-case schema normalization (`updated_utc`)

## Safety Checklist
- [ ] `git diff origin/main...HEAD -- src/hongstr` is empty
- [ ] `_local/telegram_cp/tg_cp_server.py` contains no `subprocess|os.system|Popen`
- [ ] `git status --porcelain | rg '^.. data/'` returns empty
- [ ] `./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py` passes

## Rollback
- Revert merged commit(s): `git revert <merge_commit_sha>`
- Re-run refresh and smoke checks:
  - `bash scripts/refresh_state.sh`
  - `./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py`
