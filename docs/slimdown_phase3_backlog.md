# HONGSTR Slimdown Phase 3 Backlog

Last updated (UTC): 2026-02-25  
Scan evidence: `reports/slimdown_scan_20260225T161241Z.log`

## Scope and Red Lines

- stability-first: `src/hongstr/**` core diff must remain `0`.
- tg_cp remains read-only (no `subprocess` / `os.system` / `Popen` / shell execution).
- ML/Research defaults to `report_only`.
- no `data/**` artifacts are committed.
- GitHub is SSOT: each change goes through commit + push + PR.

## 1) Writers to `data/state` (current inventory)

### Primary writer (canonical snapshot producer)
- [`scripts/state_snapshots.py`](/Users/hong/Projects/HONGSTR/scripts/state_snapshots.py)
  - writer function: `scripts/state_snapshots.py:98`
  - writes: `coverage_latest.json` (`:122`), `coverage_summary.json` (`:152`), `strategy_pool_summary.json` (`:182`), `regime_monitor_summary.json` (`:202`), `freshness_table.json` (`:265`), `execution_mode.json` (`:272`), `services_heartbeat.json` (`:310`), `coverage_matrix_latest.json` (`:381`), `system_health_latest.json` (`:537`)

### Additional direct writers (to be converged)
- [`scripts/coverage_update.py`](/Users/hong/Projects/HONGSTR/scripts/coverage_update.py): `STATE_FILE = data/state/coverage_table.jsonl` (`:16`)
- [`scripts/semantics_check.py`](/Users/hong/Projects/HONGSTR/scripts/semantics_check.py): `STATE_FILE = data/state/coverage_table.jsonl` (`:13`)
- [`scripts/phase4_regime_monitor.py`](/Users/hong/Projects/HONGSTR/scripts/phase4_regime_monitor.py): writes `data/state/regime_monitor_latest.json` (`:168`)
- [`scripts/brake_healthcheck.py`](/Users/hong/Projects/HONGSTR/scripts/brake_healthcheck.py): writes `data/state/brake_health_latest.json` (`:19`)

## 2) Secondary Computations / Fallbacks

### tg_cp (`_local/telegram_cp/tg_cp_server.py`)
- `_status_short_report()` uses health-pack-first and keeps fallback branch for missing health pack (`:542`)
- `_collect_snapshot()` folds status from logs + multiple artifacts (`:735`)
- `skill_status_overview()` recomputes monitoring summary from snapshot (`:961`)
- status file priority points to `system_health_latest.json` (`:371`)

### dashboard API (`web/app/api/status/route.ts`)
- `buildCoverageSummary()` computes from `reports/walkforward_latest.json` + optional CSV parsing (`:319`)
- `buildTimeline()` tails execution JSONL files (`:352`, `:354-355`)
- `listBacktestRuns()` performs filesystem scan of backtest run directories (`:412`)
- warnings depend on optional fallback data availability (`:510-514`)

### script-side fallback hotspots (non-core)
- coverage + semantics logic around `data/state/coverage_table.jsonl`:
  - `scripts/coverage_update.py` (`:16`)
  - `scripts/semantics_check.py` (`:13`)
- regime fallback source selection: `scripts/phase4_regime_monitor.py` (`fallback_fragment` path around `:39`)
- brake fallback manual scan: `scripts/brake_healthcheck.py` (`:39-43`)

## 3) launchd Jobs by Plane

### Data Plane
- `com.hongstr.daily_etl`
- `com.hongstr.weekly_backfill`
- `com.hongstr.realtime_ws`
- `com.hongstr.retention_cleanup`
- `com.hongstr.daily_backtest`

### State Plane
- `com.hongstr.daily_healthcheck`
- (refresh-state chain currently manual/script-triggered, not a single dedicated launchd job)

### Control Plane
- `com.hongstr.dashboard`
- `com.hongstr.tg_cp`

### Overlap / consolidation opportunities
- State snapshots currently depend on outputs written by multiple scripts (`coverage_update`, `semantics_check`, `phase4_regime_monitor`, `brake_healthcheck`) instead of a single final writer boundary.
- `daily_healthcheck` and `refresh_state` have adjacent responsibilities but no unified state-plane orchestration contract.

## 4) Minimal PR Split Plan (PR-S1 ~ PR-S6)

### PR-S1: Converge `data/state` writer boundary (minimal code refactor)
What
- Make `scripts/state_snapshots.py` the only script that writes canonical `data/state/*.json` snapshots.
- Move atomic producer outputs from direct `data/state` writes to atomic artifacts, then aggregate to `data/state` in `state_snapshots.py`.
Why
- Remove multi-writer drift and establish single writer contract for state-plane.
Risk
- Medium (touches producer wiring/order and artifact paths).
Safety
- `src/hongstr/**` unchanged, tg_cp no-exec unchanged, no `data/**` committed.
Rollback
- `git revert <merge_commit_sha>`
Verify
- run `bash scripts/refresh_state.sh`, verify `data/state/*` produced and `/status` still healthy.

### PR-S2: Refresh pipeline sequencing and ownership
What
- Update `scripts/refresh_state.sh` to explicitly run atomic producers in a deterministic order before snapshot aggregation.
Why
- Avoid stale cross-file timestamps and partial state.
Risk
- Low-Medium (runtime sequencing only).
Safety
- core untouched; no tg_cp behavior change.
Rollback
- revert commit.
Verify
- compare mtimes and schema presence across freshness/coverage/brake/regime/system_health snapshots.

### PR-S3: tg_cp `/status` fallback slimming
What
- Keep health-pack-first behavior and simplify fallback branch to `UNKNOWN + refresh hint` when health pack is missing/unreadable.
Why
- Reduce consumer-side secondary computation.
Risk
- Medium (changes status-text behavior during missing-data incidents).
Safety
- no exec, no writes, no core change.
Rollback
- revert commit.
Verify
- smoke tests + manual `/status` with and without `system_health_latest.json`.

### PR-S4: dashboard API strict SSOT mode
What
- Keep run/timeline views, but isolate top-level status cards to SSOT snapshots only.
Why
- Prevent dynamic status drift between dashboard and tg_cp.
Risk
- Low-Medium (API payload behavior adjustments).
Safety
- non-core only.
Rollback
- revert commit.
Verify
- dashboard `/api/status` retains required fields and consistent status semantics.

### PR-S5: launchd responsibility cleanup (docs + plists)
What
- Document and optionally consolidate schedule ownership into Data / State / Control planes.
Why
- Reduce duplicate scheduling and troubleshooting ambiguity.
Risk
- Medium (ops scheduling).
Safety
- no core semantics change.
Rollback
- restore previous plist and revert docs.
Verify
- launchctl list/print checks and service restart sanity.

### PR-S6: guardrail enforcement dedupe
What
- Align guardrail script checks with Global Red Lines and remove duplicate/partial variants.
Why
- Single policy source with deterministic enforcement.
Risk
- Low.
Safety
- docs/scripts only.
Rollback
- revert commit.
Verify
- guardrail scripts pass/fail expected cases consistently.

## 5) Required Verification Gates (every PR)

```bash
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py
git diff --name-only origin/main...HEAD | rg '^src/hongstr/'
git status --porcelain | rg '^.. data/'
```

