# Leaderboard Zero Metrics Audit (2026-02-27)

## Scope

- `research/loop/research_loop.py`
- `research/loop/leaderboard.py`
- `research/loop/gates.py`
- `research/loop/weekly_governance.py`
- `scripts/state_snapshots.py`
- `scripts/refresh_state.sh`
- `docs/governance/direction_variants_reporting.md`

## Symptom

After `bash scripts/refresh_state.sh`, TL;DR showed valid strategy IDs under `Strategy Pool Leaders`, but `Score/Sharpe/Return` appeared as `0.00`.

## Deterministic Root Cause

The `0.00` values were not always real measured performance. They were produced by fallback/default coercion across the report-only path:

1. Dry-run artifacts encoded unavailable metrics as numeric zeros.
   - `research_loop.run_backtest_simulated(..., dry_run=True)` returned `oos_sharpe=0.0`, `oos_mdd=0.0`, `pnl_mult=1.0`, etc.
2. Summary construction used zero defaults.
   - `_build_summary()` used `metrics.get(..., 0.0)` and computed `total_return` from default `pnl_mult=1.0` -> `0.0`.
3. Strategy pool records persisted these zeros.
   - `records.append(...)` used defaults like `last_score=...0.0`, `last_oos_metrics.sharpe=...0.0`.
4. SSOT snapshot generation also defaulted missing values to `0`.
   - `scripts/state_snapshots.py` previously built `strategy_pool_summary.leaderboard` with `.get(..., 0)`.
5. TL;DR formatter always printed numeric format.
   - `scripts/refresh_state.sh` rendered `Score/Sharpe/Return` via `:.2f`, so unavailable metrics surfaced as `0.00`.
6. Research leaderboard parser also defaulted missing metrics to `0.0`.
   - `research/loop/leaderboard.py` used `_as_float(..., 0.0)` in entry parsing, which masked missing/unavailable states.

## Correct Behavior

- If metrics are unavailable, output should be explicit `UNKNOWN`/`null` with reason.
- Numeric `0.00` should be used only when metric value is truly zero, not when data is unavailable.

## Fix Implemented

### 1) Research loop writes unavailable metrics as explicit unknown

- In dry-run simulation, metrics now return `None` (not numeric zero).
- `_build_summary()` now computes:
  - typed optional metrics (`None` when unavailable),
  - `metrics_status` (`OK`/`UNKNOWN`),
  - `metrics_unavailable_reason` (for example `dry_run_artifact`).
- When summary metrics are `UNKNOWN`, report score/gate fields are nulled (`final_score=None`, `gate_overall=UNKNOWN`) instead of forced zero.
- Strategy-pool records now preserve nullable metrics instead of defaulting to `0.0`.

### 2) Leaderboard parser preserves unknown instead of coercing to zero

- `research/loop/leaderboard.py` now:
  - parses metrics as optional values,
  - emits `metrics_status` + `metrics_unavailable_reason`,
  - maps `status=DRY_RUN` artifacts to `None` metrics even if older artifacts contain `0`,
  - ranks with `None -> -inf` (unknown rows sink to bottom, not interpreted as real `0.0`).

### 3) Strategy pool snapshot and TL;DR are explicit about unknown

- `scripts/state_snapshots.py` now writes nullable leaderboard metrics and availability fields:
  - `metrics_status`
  - `metrics_unavailable_reason`
- `scripts/refresh_state.sh` TL;DR now renders unavailable values as `UNKNOWN` instead of `0.00`.

### 4) Governance expectation documented

- `docs/governance/direction_variants_reporting.md` now states:
  - unavailable metrics must be `null` + `UNKNOWN reason`,
  - unavailable metrics must not be coerced to `0.00`.

## Test Coverage Added

New tests in `research/loop/tests/test_leaderboard_metrics.py`:

1. `metrics present -> non-zero values propagate`
2. `dry-run metrics -> UNKNOWN/null (not 0)`
3. `metrics missing -> UNKNOWN with reason (not 0)`

Existing research loop tests and direction tests continue to validate compatibility.

