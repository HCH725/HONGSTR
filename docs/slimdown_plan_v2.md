# HONGSTR Slimdown Plan v2 (Docs-Only Planning Pass)

Last updated (UTC): 2026-02-25T15:39:15Z  
Branch baseline: `main@8e64719`

## 1) Writers to `data/state` (Classification)

### A. SSOT writer (keep)

| Item | Evidence | Decision |
|---|---|---|
| `scripts/refresh_state.sh` (orchestrator) | `scripts/refresh_state.sh:28-29`, `scripts/refresh_state.sh:46-47` | Keep as the only entrypoint operators run for SSOT refresh. |
| `scripts/state_snapshots.py` (canonical snapshot writer) | `scripts/state_snapshots.py:98-102`, writes at `:122`, `:152`, `:182`, `:202-206`, `:265`, `:272`, `:310`, `:381`, `:537` | Keep as canonical writer for dashboard/control-plane snapshots, including `system_health_latest.json`. |

### B. Allowed atomic producers (keep, but feed SSOT)

| Item | Evidence | Decision |
|---|---|---|
| `scripts/coverage_update.py` -> `coverage_table.jsonl` | `scripts/coverage_update.py:16`, `:103-105` | Keep. It is upstream input for coverage snapshots. |
| `scripts/semantics_check.py` -> mutates `coverage_table.jsonl` | `scripts/semantics_check.py:13`, `:55-57` | Keep for now. Semantics gate is still used to stamp `NEEDS_REBASE`. |
| `scripts/phase4_regime_monitor.py` -> `regime_monitor_latest.json` | `scripts/phase4_regime_monitor.py:168-169` | Keep. Regime signal producer remains report-only. |
| `scripts/brake_healthcheck.py` -> `brake_health_latest.json` | `scripts/brake_healthcheck.py:19`, `:117-119` | Keep as atomic health producer until state-plane consolidation lands. |

### C. Should be removed or converged (next step)

| Item | Evidence | Planned change |
|---|---|---|
| Producer scheduling split (regime/brake not in refresh pipeline) | `scripts/refresh_state.sh` currently only runs coverage update + snapshots (`:28-29`, `:46-47`) | Converge: run regime + brake producers before `state_snapshots.py` inside state plane. |
| `subprocess` fallback in brake producer | `scripts/brake_healthcheck.py:12`, `:35-46` | Remove helper-script subprocess path; keep pure file scan to reduce hidden side effects. |

## 2) Consumer-side Secondary Computation (KEEP vs REMOVE)

### A. tg_cp (`_local/telegram_cp/tg_cp_server.py`)

| Location | Current behavior | Decision |
|---|---|---|
| `_status_short_report()` fallback branch (`:574-735`) | If `system_health_latest.json` is missing/unreadable, locally recomputes statuses from component files. | **KEEP (temporary)** for resilience; target to simplify in PR2 once state-plane job guarantees health-pack freshness. |
| `_collect_snapshot()` (`:767-924`) | Computes ops snapshot from log tails and several artifacts (dashboard, ETL, coverage fold). | **KEEP** as ops diagnostic surface, but keep it out of `SSOT_STATUS` semantics. |
| `skill_status_overview()` (`:993-1051`) | Recomputes freshness/coverage/brake text summary from `_collect_snapshot()`. | **KEEP** as skill-level diagnostics; not a blocker for `/status` SSOT path. |
| `_read_coverage_table_rebase()` (`:455-485`) | Unused helper (no callsite). | **REMOVE** in next safe refactor PR. |
| Router regime field mismatch (`_local/telegram_cp/router.py:30-32`) | Reads `snapshot.regime_monitor.status`, while raw regime snapshot uses `overall`. | **REMOVE/ADAPT** in PR2 to avoid silent trigger drift. |

### B. Dashboard (`web/app/api/status/route.ts`)

| Location | Current behavior | Decision |
|---|---|---|
| `buildStatus()` (`:235-275`) | Reads `execution_mode.json` + `services_heartbeat.json` from SSOT files. | **KEEP** (already SSOT-first). |
| `buildCoverageMatrix()` (`:386-395`) | Reads `coverage_matrix_latest.json` snapshot directly. | **KEEP** (already SSOT-first). |
| `buildRegimeMonitor()` (`:397-405`) | Reads `regime_monitor_summary.json` snapshot directly. | **KEEP** (already SSOT-first). |
| `buildCoverageSummary()` (`:319-349`) | Reads `reports/walkforward_latest.json` and optional CSV timestamp parse. | **KEEP** (analytics detail; not `SSOT_STATUS` computation). |
| `listBacktestRuns()` (`:412-468`) + selection fallback (`:492-495`) | Scans run directories; falls back to global selection artifact. | **KEEP** (UI run-browsing feature), outside core status rollup. |

## 3) launchd Map (Single Responsibility + Merge Proposal)

Scanned jobs: `launchctl list` + `~/Library/LaunchAgents/com.hongstr.*.plist`.

| Job | ProgramArguments target | Plane | Unique responsibility | Consolidation note |
|---|---|---|---|---|
| `com.hongstr.daily_etl` | `scripts/daily_etl.sh` | Data | Daily ingestion/update | Keep. |
| `com.hongstr.weekly_backfill` | `scripts/backfill_1m_from_2020.sh` | Data | Weekly long-range backfill | Keep. |
| `com.hongstr.realtime_ws` | `scripts/run_realtime_service.sh` | Data | Realtime stream service | Keep. |
| `com.hongstr.retention_cleanup` | `scripts/retention_cleanup.sh` | Data | Retention and cleanup | Keep. |
| `com.hongstr.daily_backtest` | `scripts/daily_backtest.sh` | Compute | Daily backtest run | Keep. |
| `com.hongstr.daily_healthcheck` | `scripts/daily_backtest_healthcheck.sh` | State | Healthcheck report | Candidate merge into state-plane refresh chain. |
| `com.hongstr.dashboard` | `streamlit run scripts/dashboard.py` | Control | Dashboard serving | Keep. |
| `com.hongstr.tg_cp` | `_local/telegram_cp/tg_cp_server.py` | Control | Telegram control-plane bot | Keep (read-only invariant). |
| `com.hongstr.research_poller` | `scripts/poll_research_loop.sh` | Research | Poll/trigger research loop | Keep as single scheduler. |
| `com.hongstr.research_loop` | `scripts/run_research_loop.sh --once` | Research | One-shot research loop execution | Candidate: keep executable but drop duplicate schedule owner. |

## 4) Proposed PR Sequence (2-3 PRs)

### PR1 (this PR, docs-only)
- Add:
  - `docs/slimdown_plan_v2.md`
  - `docs/guardrails_dedupe.md`
- No behavior change.

### PR2 (minimal refactor, safe scope)
- `scripts/refresh_state.sh`
  - Add explicit state-plane chain: regime producer -> brake producer -> `state_snapshots.py`.
- `_local/telegram_cp/tg_cp_server.py`
  - Remove dead helper `_read_coverage_table_rebase()`.
  - Keep `/status` health-pack-first behavior; shrink fallback path to strict UNKNOWN+action when sources are missing/unreadable (avoid local re-derivation drift).
- `_local/telegram_cp/router.py`
  - Align regime trigger with canonical field (`overall` or normalized adapter).

### PR3 (optional schedule consolidation)
- Launchd docs + plist housekeeping:
  - define one state-plane owner job for refresh chain.
  - keep data/control/research planes separated.

## 5) Safety Checklist (must pass for every PR)

```bash
git diff --name-only origin/main...HEAD | rg '^src/hongstr/' && exit 1 || true
rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py && exit 1 || true
git status --porcelain | rg '^.. data/' && exit 1 || true
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
```

## 6) Rollback

```bash
git revert <merge_commit_sha>
bash scripts/refresh_state.sh
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
```

