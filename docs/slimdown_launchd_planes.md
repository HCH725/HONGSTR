# HONGSTR Launchd Planes (Slimdown P1)

Last updated (UTC): 2026-02-25T17:38:42Z
Evidence:
- `reports/slimdown_fullscan_2026-02-25T173842Z.log`
- `~/Library/LaunchAgents/com.hongstr.*.plist` (`plutil -p`)

## Scope

This is a docs-only planning artifact for schedule consolidation.
No plist/runtime behavior change in this PR.

## Plane Mapping

| Plane | Label | Trigger | Program | Single responsibility |
|---|---|---|---|---|
| Data | `com.hongstr.daily_etl` | daily `02:00` | `scripts/daily_etl.sh` | Build/refresh derived market data. |
| Data | `com.hongstr.weekly_backfill` | weekly Sun `03:30` | `scripts/backfill_1m_from_2020.sh` | Long-range data backfill. |
| Data | `com.hongstr.realtime_ws` | `RunAtLoad` + `KeepAlive` | `scripts/run_realtime_service.sh` | Continuous realtime ingestion. |
| Data | `com.hongstr.retention_cleanup` | daily `03:00` | `scripts/retention_cleanup.sh` | Retention cleanup only. |
| Data | `com.hongstr.daily_backtest` | daily `05:00` | `scripts/daily_backtest.sh` | Produce daily backtest runs/artifacts. |
| State | `com.hongstr.daily_healthcheck` | daily `02:30` | `scripts/daily_backtest_healthcheck.sh` | Validate backtest/data readiness and write health CSV report. |
| Control | `com.hongstr.dashboard` | `RunAtLoad` + `KeepAlive` | `streamlit run scripts/dashboard.py` | Read-only dashboard serving. |
| Control | `com.hongstr.tg_cp` | `RunAtLoad` + `KeepAlive` | `_local/telegram_cp/tg_cp_server.py` | Read-only Telegram control plane. |
| Research | `com.hongstr.research_loop` | daily `06:20` (`--once`) | `scripts/run_research_loop.sh` | Scheduled report-only research loop run. |
| Research | `com.hongstr.research_poller` | every `600s` + `RunAtLoad` | `scripts/poll_research_loop.sh` | Queue polling and report-only trigger handling. |

## Overlap and Gaps

1. State-plane ownership is ambiguous:
- Canonical SSOT builder is `scripts/refresh_state.sh` + `scripts/state_snapshots.py`.
- There is no dedicated launchd job for this state refresh chain.

2. Naming/intent overlap:
- `daily_healthcheck` label sounds generic "system health", but currently runs `daily_backtest_healthcheck.sh` (data/backtest validation scope).

3. Research scheduling overlap:
- `research_loop` (scheduled once/day) and `research_poller` (continuous polling) can both trigger report generation paths; ownership and precedence should be explicit in docs.

## Minimal Consolidation Sequence (No Risky Deletion)

### P1 (this docs pass)
- Freeze plane mapping and single responsibility per job.
- Keep runtime unchanged.

### P2 (small ops/docs follow-up)
- Add a state-plane launchd entry for `scripts/refresh_state.sh` with deterministic timing after ETL.
- Clarify `daily_healthcheck` role in docs as validator, not SSOT producer.

### P3 (small ops cleanup after observation)
- Decide one primary research trigger owner (`research_loop` schedule vs `research_poller` queue-first), keep the other as backup path.
- Document rollback (`launchctl bootout/bootstrap` using prior plist).

## Red-line Verification (every PR)

```bash
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py
git diff --name-only origin/main...HEAD | rg '^src/hongstr/'
git status --porcelain | rg '^.. data/'
```

## Rollback

```bash
git revert <merge_commit_sha>
```

