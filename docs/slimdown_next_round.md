# HONGSTR Slimdown Next Round Plan (Stability-First)

Last updated (UTC): 2026-02-25
Baseline commit: `main@89cedb5`
Scan evidence:
- `reports/slimdown_full_scan_2026-02-25T165451Z.log`
- `reports/slimdown_nextscan_2026-02-25T170040Z.log`
- `reports/slimdown_fullscan_2026-02-25T173842Z.log`
- `reports/slimdown_next_actions_2026-02-25T173842Z.md`

## Red Lines (must hold every PR)

- `src/hongstr/**` core diff = 0
- `tg_cp` no exec (`subprocess` / `os.system` / `Popen` forbidden)
- ML/Research defaults to `report_only`
- no `data/**` runtime artifacts committed
- GitHub SSOT flow only (commit + push + PR)

## A) Current P0 Status (from latest scans)

### P0-1 Status-class SSOT-only

Done:
- `tg_cp /status` is health-pack-first and SSOT fallback only (`_local/telegram_cp/tg_cp_server.py`).
- dashboard `/api/status` top-level freshness/coverage/regime cards are SSOT-driven (`web/app/api/status/route.ts`).
- Missing/unreadable SSOT now yields UNKNOWN + refresh-hint behavior in both tg_cp and dashboard status paths.
- `skill_status_overview()` now delegates to `_status_short_report()` (SSOT path), not `_collect_snapshot()` fold logic.

Remaining gaps:
- none for status-class output; `_collect_snapshot()` remains for non-status detail skills.

### P0-2 State writer boundary

Done:
- atomic producers write to `reports/state_atomic/*`:
  - `scripts/coverage_update.py`
  - `scripts/semantics_check.py`
  - `scripts/phase4_regime_monitor.py`
  - `scripts/brake_healthcheck.py`
- canonical writer for dashboard/control-plane state snapshots is `scripts/state_snapshots.py`.
- `scripts/semantics_check.py` no longer falls back to `data/state/coverage_table.jsonl`.
- `scripts/state_snapshots.py` no longer falls back to canonical `data/state/*` for coverage/regime/brake upstream inputs.

Remaining gaps:
- schedule/ops ownership still needs explicit state-plane job ownership (see P1 docs below).

## B) launchd Planes (P1 docs-only)

Detailed mapping and consolidation notes:
- `docs/slimdown_launchd_planes.md`

| Plane | Jobs | One-line responsibility | Overlap |
|---|---|---|---|
| Data | `daily_etl`, `weekly_backfill`, `realtime_ws`, `retention_cleanup`, `daily_backtest` | Produce/maintain raw+derived market data and backtest runs | `daily_backtest` output freshness is also consumed by state health checks |
| State | `daily_healthcheck` + `scripts/refresh_state.sh` chain | Build canonical `data/state/*` snapshots for dashboard/tg_cp | `daily_healthcheck` responsibility overlaps with refresh-state summary checks |
| Control | `dashboard`, `tg_cp` | Read-only serving and status delivery | none (if status stays SSOT-only) |
| Research | `research_loop`, `research_poller` | report-only research orchestration | scheduling owner overlap between loop/poller |

### Minimal consolidation proposal (no destructive schedule change yet)

1. Keep existing jobs, but document `refresh_state.sh` as state-plane source-of-truth builder.
2. Reframe `daily_healthcheck` as state-plane validator only (no competing status recompute semantics).
3. Keep control plane strictly read-only against canonical `data/state/*`.

## C) Next PR Slices

### Completed

- PR #65: docs planning (`docs/slimdown_next_round.md`)
- PR #66: P0 minimal refactor (status SSOT path + writer boundary fallback removal)

### PR-P1 (this PR) launchd planes docs-only

What
- Add `docs/slimdown_launchd_planes.md` with current launchd job -> plane mapping and overlap/gap notes.

Why
- Make schedule ownership explicit before any plist change.

Risk
- Low (docs-only).

Safety
- no non-doc code changes.

Rollback
- `git revert <merge_commit_sha>`

Verify
- file exists and CI passes.

### PR-P2 small ops follow-up (after observation)

What
- Add/clarify a state-plane schedule owner for `scripts/refresh_state.sh` without deleting existing jobs.

Why
- Reduce ambiguity between validation jobs and canonical SSOT snapshot production.

Risk
- Low to medium (ops schedule timing only).

Safety
- core untouched, tg_cp no-exec unchanged, no data artifacts committed.

Rollback
- `git revert <merge_commit_sha>`

Verify
- `./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py`
- `rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py`
- `git diff --name-only origin/main...HEAD | rg '^src/hongstr/'`
- `git status --porcelain | rg '^.. data/'`

### PR-P3 research-trigger ownership cleanup (optional)

What
- Choose one primary research trigger owner (`research_loop` vs `research_poller`) and document backup path.

Why
- reduce operational ambiguity without risky job deletion.

Risk
- Low.

Safety
- docs/plist hygiene only; no core runtime behavior changes.

Rollback
- revert commit(s).

Verify
- launchd docs and checklist references consistent with actual plists.
