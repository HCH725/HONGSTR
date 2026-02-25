# HONGSTR Launchd 3-Plane Responsibility Map

Last updated (UTC): 2026-02-25T18:13:36Z  
Evidence:
- `reports/slimdown_full_scan_2026-02-25T175644Z.log`
- `~/Library/LaunchAgents/com.hongstr.*.plist` (`plutil -p`)

## Scope

This is a docs-only consolidation map.  
No launchd plist/runtime behavior change is included here.

## 3-Plane Model (Target)

- Data Plane: ETL/backfill/retention/realtime_ws (+ daily backtest artifact generation).
- State Plane: `refresh_state` as the canonical SSOT writer entrypoint for `data/state/*`.
- Control Plane: `tg_cp` + dashboard as SSOT-only consumers (no status recompute).

## State Plane: Single Owner Of SSOT Write Boundary

- Canonical writer boundary: only `scripts/state_snapshots.py` writes canonical `data/state/*` snapshots.
- Canonical orchestrator: `scripts/refresh_state.sh` is the only State Plane entrypoint that calls atomic producers and then `state_snapshots.py`.
- Non-State jobs (Data/Control/Research) must not directly publish canonical SSOT snapshots to `data/state/*`.

## Job Responsibility Map (Current)

| Plane | Label | Trigger | Single responsibility (one sentence) |
|---|---|---|---|
| Data | `com.hongstr.daily_etl` | daily `02:00` | Refresh market data/derived inputs for downstream consumers. |
| Data | `com.hongstr.weekly_backfill` | weekly Sun `03:30` | Backfill historical 1m data range gaps. |
| Data | `com.hongstr.realtime_ws` | `RunAtLoad` + `KeepAlive` | Keep realtime stream ingestion running continuously. |
| Data | `com.hongstr.retention_cleanup` | daily `03:00` | Prune old runtime artifacts/logs by retention policy. |
| Data | `com.hongstr.daily_backtest` | daily `05:00` | Produce a daily backtest run and research/backtest artifacts. |
| State | `refresh_state` (script chain) | on-demand / scheduler TBD | Run atomic producers and `state_snapshots.py` to write canonical `data/state/*`. |
| State | `com.hongstr.daily_healthcheck` | daily `02:30` | Validate data/backtest readiness only (validator), not canonical state ownership. |
| Control | `com.hongstr.dashboard` | `RunAtLoad` + `KeepAlive` | Serve read-only UI using SSOT state files. |
| Control | `com.hongstr.tg_cp` | `RunAtLoad` + `KeepAlive` | Serve read-only Telegram status/ops interface from SSOT state files. |
| Control | `com.hongstr.research_poller` | every `600s` + `RunAtLoad` | Poll research queue and trigger report-only research jobs. |
| Control | `com.hongstr.research_loop` | daily `06:20` (`--once`) | Run scheduled report-only research loop once per cycle. |

## Overlap Checklist

- [ ] `daily_healthcheck` does not claim canonical `data/state/*` ownership; it remains validator-only.
- [ ] `refresh_state` is the only canonical state writer entrypoint (via `state_snapshots.py`).
- [ ] dashboard/tg_cp status paths do not compute status from derived/log/artifacts.
- [ ] `research_poller` vs `research_loop` ownership is explicit (primary vs backup trigger path).
- [ ] `daily_backtest` output responsibilities are separated from state publication responsibilities.

## Current Overlap / Concern Notes

1. `daily_healthcheck` vs `refresh_state`
- Concern: both are perceived as "health" jobs; ownership can be misunderstood.
- Direction: `daily_healthcheck` = validator, `refresh_state` = canonical SSOT publisher.

2. `research_poller` vs `research_loop`
- Concern: two independent trigger paths can both produce report-only outputs.
- Direction: choose one primary trigger owner; the other should be off-by-default or strictly read-only backup trigger.

3. State-plane scheduling gap
- Concern: canonical `refresh_state` does not yet have a clearly documented dedicated launchd owner.
- Direction: add/clarify state-plane schedule in a small ops PR after this docs pass.

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
