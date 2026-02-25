# HONGSTR Slimdown Next Round Plan (Stability-First)

Last updated (UTC): 2026-02-25
Baseline commit: `main@6386f74`
Scan evidence:
- `reports/slimdown_full_scan_2026-02-25T165451Z.log`
- `reports/slimdown_nextscan_2026-02-25T170040Z.log`

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

Remaining gaps:
- `skill_status_overview()` still computes status-like output via `_collect_snapshot()` (log/report fold path), not via canonical SSOT-only `/status` formatter.
- `_collect_snapshot()` remains necessary for detail/ops context, but should not drive status-class outputs.

### P0-2 State writer boundary

Done:
- atomic producers write to `reports/state_atomic/*`:
  - `scripts/coverage_update.py`
  - `scripts/semantics_check.py`
  - `scripts/phase4_regime_monitor.py`
  - `scripts/brake_healthcheck.py`
- canonical writer for dashboard/control-plane state snapshots is `scripts/state_snapshots.py`.

Remaining gaps:
- `scripts/state_snapshots.py` still has legacy read fallbacks from `data/state/*` for some inputs (coverage/regime/brake), weakening strict writer boundary.
- `scripts/semantics_check.py` still keeps legacy read fallback from `data/state/coverage_table.jsonl`.

## B) launchd Planes (P1 docs-only)

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

### PR-N1 (this PR) docs-only planning

What
- Add `docs/slimdown_next_round.md` with current gap map and small-step execution slices.

Why
- Freeze scope and avoid uncontrolled refactor drift.

Risk
- Low (docs-only).

Safety
- no non-doc code changes.

Rollback
- `git revert <merge_commit_sha>`

Verify
- file exists and CI passes.

### PR-N2 minimal refactor (P0-only)

What
- `tg_cp`: make `skill_status_overview()` delegate to SSOT `/status` report path (no `_collect_snapshot()` fold for status-class output).
- `state writer boundary`: make state snapshot assembly read atomic producer outputs first and drop legacy `data/state/*` fallback for upstream producer inputs where safe.

Why
- complete SSOT-only status behavior and tighten single-writer contract.

Risk
- Low to medium (non-core glue/pathing only).

Safety
- core untouched, tg_cp no-exec unchanged, no data artifacts committed.

Rollback
- `git revert <merge_commit_sha>`

Verify
- `./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py`
- `rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py`
- `git diff --name-only origin/main...HEAD | rg '^src/hongstr/'`
- `git status --porcelain | rg '^.. data/'`

### PR-N3 schedule cleanup docs/ops follow-up (optional)

What
- Update launchd runbook/docs to mark state-plane single ownership and overlap resolution steps.

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
