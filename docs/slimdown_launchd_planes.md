# HONGSTR Launchd 3-Plane Responsibility Map

Last updated (UTC): 2026-02-25T18:57:00Z  
Evidence:
- `reports/slimdown_full_scan_2026-02-25T175644Z.log`
- `~/Library/LaunchAgents/com.hongstr.*.plist` (`plutil -p`)

## Scope

This is a docs-only consolidation map.  
No launchd plist/runtime behavior change is included here.

## 3-Plane Model (Target)

- Data Plane: ETL/backfill/retention workloads (plus daily backtest artifact production), no SSOT status publication.
- State Plane: `com.hongstr.refresh_state` -> `scripts/refresh_state.sh` as canonical SSOT writer entrypoint for `data/state/*`.
- Control Plane: tg_cp/dashboard/realtime_ws plus report-only research queue orchestration; status paths are SSOT-read-only.

## State Plane: Single Owner Of SSOT Write Boundary

- Canonical writer boundary: only `scripts/state_snapshots.py` writes canonical `data/state/*` snapshots.
- Canonical orchestrator: `scripts/refresh_state.sh` is the only State Plane entrypoint that calls atomic producers and then `state_snapshots.py`.
- Scheduler owner: `com.hongstr.refresh_state` runs `scripts/refresh_state.sh` every 60 minutes (`StartInterval=3600`) with `RunAtLoad=true`.
- Compatibility alias: `com.hongstr.daily_healthcheck` now calls `scripts/refresh_state.sh` at the legacy 02:30 slot; it no longer owns separate state computation.
- Non-State jobs (Data/Control/Research) must not directly publish canonical SSOT snapshots to `data/state/*`.

## Job Responsibility Map (Current)

| Plane | Label | Trigger | Single responsibility (one sentence) |
|---|---|---|---|
| Data | `com.hongstr.daily_etl` | daily `02:00` | Refresh market data/derived inputs for downstream consumers. |
| Data | `com.hongstr.weekly_backfill` | weekly Sun `03:30` | Backfill historical 1m data range gaps. |
| Data | `com.hongstr.retention_cleanup` | daily `03:00` | Prune old runtime artifacts/logs by retention policy. |
| Data | `com.hongstr.daily_backtest` | daily `05:00` | Produce a daily backtest run and research/backtest artifacts. |
| State | `com.hongstr.refresh_state` | `RunAtLoad` + every `60m` | Trigger canonical SSOT refresh chain (`scripts/refresh_state.sh` -> `scripts/state_snapshots.py`). |
| State | `com.hongstr.daily_healthcheck` | daily `02:30` | Legacy alias that triggers the same `refresh_state` chain (no independent state logic). |
| Control | `com.hongstr.dashboard` | `RunAtLoad` + `KeepAlive` | Serve read-only UI using SSOT state files. |
| Control | `com.hongstr.tg_cp` | `RunAtLoad` + `KeepAlive` | Serve read-only Telegram status/ops interface from SSOT state files. |
| Control | `com.hongstr.realtime_ws` | `RunAtLoad` + `KeepAlive` | Keep realtime streaming service running; consume existing data/services only. |
| Control | `com.hongstr.research_poller` | every `600s` + `RunAtLoad` | Queue-facing poller only (enqueue/de-dup/cooldown); no heavy research compute. |
| Control | `com.hongstr.research_loop` | daily `06:20` (`--once`) | Execute queued/scheduled research run in report-only mode; no SSOT state writing. |

## Job Ownership Sheet (`com.hongstr.*`)

| Label | Owner plane | Unique responsibility | Overlap guardrail |
|---|---|---|---|
| `com.hongstr.daily_etl` | Data | Produce/refresh ETL data inputs only. | Must not publish canonical `data/state/*` snapshots. |
| `com.hongstr.weekly_backfill` | Data | Backfill historical market data gaps. | Must not publish canonical `data/state/*` snapshots. |
| `com.hongstr.retention_cleanup` | Data | Enforce retention policy for logs/runtime artifacts. | Must not run state/status recomputation logic. |
| `com.hongstr.daily_backtest` | Data | Produce daily backtest artifacts. | Artifacts are inputs only; canonical status is published by State Plane. |
| `com.hongstr.refresh_state` | State | Canonical state orchestrator (`refresh_state.sh` -> `state_snapshots.py`). | This is the scheduler owner of SSOT publication. |
| `com.hongstr.daily_healthcheck` | State (alias/deprecated path) | Legacy alias trigger for `refresh_state.sh` only. | Must not own independent state computation or publication. |
| `com.hongstr.dashboard` | Control | Serve read-only dashboard from SSOT snapshots. | No top-level status recomputation from logs/derived/artifacts. |
| `com.hongstr.tg_cp` | Control | Serve read-only Telegram control-plane views from SSOT snapshots. | No exec actions; no non-SSOT top-level status fold. |
| `com.hongstr.realtime_ws` | Control | Keep realtime websocket collector/service alive. | Must not publish canonical `data/state/*` snapshots. |
| `com.hongstr.research_poller` | Control (Research queue) | Enqueue/de-dup/cooldown research tasks only. | Must not execute heavy research runs itself. |
| `com.hongstr.research_loop` | Control (Research runner) | Execute report-only research jobs from schedule/queue. | Must not publish canonical `data/state/*` snapshots. |

## Overlap Checklist

- [ ] `com.hongstr.refresh_state` is the canonical State Plane scheduler owner.
- [ ] `daily_healthcheck` remains alias-only and does not own separate `data/state/*` computation.
- [ ] `refresh_state` is the only canonical state writer entrypoint (via `state_snapshots.py`).
- [ ] dashboard/tg_cp status paths do not compute status from derived/log/artifacts.
- [ ] `research_poller` does queue control only; `research_loop` does execution only.
- [ ] `daily_backtest` output responsibilities are separated from state publication responsibilities.

## Current Overlap / Concern Notes

1. `daily_healthcheck` vs `refresh_state`
- Concern: both are perceived as "health" jobs; ownership can be misunderstood.
- Direction: `com.hongstr.refresh_state` = canonical SSOT scheduler/publisher; `daily_healthcheck` = legacy alias trigger only.
- Deprecation path (safe/minimal):
  - Phase A: keep `daily_healthcheck` as alias-only (calls `refresh_state.sh` and nothing else).
  - Phase B: mark `daily_healthcheck` as deprecated in docs/ops inventory and stop adding new logic there.
  - Phase C: when operations are stable, disable/remove alias schedule and keep `refresh_state` as sole scheduler owner.
  - Rollback: re-enable alias plist and bootstrap it if `refresh_state` schedule has incident risk.

2. `research_poller` vs `research_loop`
- Concern: two independent trigger paths can both produce report-only outputs.
- Direction: lock responsibilities now: `research_poller` handles queue/de-dup/cooldown only, `research_loop` executes report-only runs only.

## Migration SOP (plist change, zero-downtime mindset)

Use this standard sequence whenever changing any `com.hongstr.*.plist` to avoid duplicate instances and Telegram 409-style conflicts:

```bash
LABEL="com.hongstr.<job>"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

# 1) Unload old definition/process
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true

# 2) Wait for teardown
sleep 5

# 3) Load new definition
launchctl bootstrap "gui/$(id -u)" "$PLIST"

# 4) Verify launchd state
launchctl print "gui/$(id -u)/$LABEL" | rg 'state|pid|last exit|active count|program|ProgramArguments'
```

Single-instance verification checklist (especially for tg_cp/realtime services):

```bash
# A) Only one launchd service active for the label
launchctl print "gui/$(id -u)/com.hongstr.tg_cp" | rg 'state =|pid =|active count'

# B) Only one process instance
pgrep -af "tg_cp_server.py"
```

Interpretation:
- `active count` should indicate a single active service.
- `pgrep` should show one expected runtime instance for the target daemon.
- If more than one instance appears, repeat `bootout -> wait -> bootstrap` and verify again before declaring rollout complete.

## Success Criteria

- Only `scripts/state_snapshots.py` writes canonical `data/state/*` (invoked by `scripts/refresh_state.sh` orchestrator).
- Consumers (dashboard/tg_cp and related status APIs) only read SSOT state and do not recompute top-level status.
- Each launchd job has one explicit responsibility with no overlap in ownership.

## Verification Commands (PR description copy-ready)

```bash
git diff --name-only origin/main...HEAD | rg '^src/hongstr/' || true
git status --porcelain | rg '^.. data/' && exit 1 || true
rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py && exit 1 || true
```

## Rollback

```bash
git revert <merge_commit_sha>
```
