# HONGSTR Dashboard Canonical State Audit (R5-D)

## 1) Objective

Verify whether the dashboard uses canonical state files under `data/state/**` (and other persisted artifacts), or computes health/status dynamically at request time.

## 2) Canonical state inventory (FOUND)

The following files are verified as canonical state sources:

- **`data/state/freshness_table.json`**: Unified 3x3 data age matrix.
- **`data/state/brake_health_latest.json`**: System health status (freshness, regime, artifacts).
- **`data/state/regime_monitor_summary.json`**: Summarized regime drift/anomaly status.
- **`data/state/strategy_pool_summary.json`**: Strategy leaderboard and pool counts.
- **`data/state/coverage_summary.json`**: Global coverage pass rate and Sharpe stats.
- **`reports/benchmark_latest.json`**: Strategy vs Benchmark returns.
- **`reports/walkforward_latest.json`**: Walkforward window completion status.
- **`data/reports/daily_backtest_health.csv`**: Time-series history of backtest health.

## 3) Dashboard entrypoints & Data Access

- **Primary API**: `web/app/api/status/route.ts`
  - Reads `data/state/**` using `readJsonArtifact` (canonical).
  - Accesses `data/backtests/` via dynamic directory scanning (dynamic).
  - Accesses `data/state/coverage_table.jsonl` and tails last 1000 lines to compute matrix (dynamic).

## 4) Findings per dashboard section

| Section | Data Source(s) | Producer Script | Consumer Component | Nature | Status |
|---|---|---|---|---|---|
| **Freshness** | `data/state/freshness_table.json` | `scripts/state_snapshots.py` | `FreshnessGrid` | Canonical | **FOUND** |
| **Brake Health** | `data/state/brake_health_latest.json` | `scripts/brake_healthcheck.py` | `BrakeStatusCard` | Canonical | **FOUND** |
| **Regime Monitor** | `data/state/regime_monitor_summary.json` | `scripts/state_snapshots.py` | `RegimeCard` | Canonical | **FOUND** |
| **Coverage Summary** | `reports/walkforward_latest.json` | `scripts/report_walkforward.py` | `CoverageSummary` | Canonical | **FOUND** |
| **Coverage Matrix** | `data/state/coverage_table.jsonl` | `scripts/coverage_update.py` | `CoverageMatrix` | **Dynamic** | **FOUND** |
| **Timeline** | `data/state/execution_*.jsonl` | `scripts/run_all_paper.py` | `EventTimeline` | Canonical | **FOUND** |
| **Strategy Pool** | `data/state/strategy_pool_summary.json` | `scripts/state_snapshots.py` | `Leaderboard` | Canonical | **FOUND** |
| **Execution Mode** | `data/state/execution_mode.json` | **MISSING** | `StatusHeader` | Canonical | **AMBIGUOUS** |
| **Services Heartbeat** | `data/state/services_heartbeat.json` | **MISSING** | `ServicesList` | Canonical | **AMBIGUOUS** |

### Notes

- **Coverage Matrix**: Currently reads the large `.jsonl` file and computes stats on the fly. This should be moved to `state_snapshots.py` for performance.
- **Ambiguous Producers**: `execution_mode.json` and `services_heartbeat.json` are consumed by the API but no primary writing script exists in the repo. They are likely handled by a legacy process or external orchestration currently not under version control.

## 5) Recommendation (next minimal PR)

- **Consolidation**: Update `scripts/state_snapshots.py` to also produce the `CoverageMatrixSummary` (done/in_progress/blocked counts) so `route.ts` can stop parsing raw `.jsonl` files.
- **Heartbeat Implementation**: Create a small script (e.g., `scripts/update_heartbeats.py`) that aggregates launchd log status and writes to `data/state/services_heartbeat.json` to fulfill the dashboard's service list.
- **Traceability**: Update `docs/brakes.md` to correctly point to `state_snapshots.py` for the Freshness table.
