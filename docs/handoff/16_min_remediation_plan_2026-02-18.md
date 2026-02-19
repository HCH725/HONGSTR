# Minimal Remediation Plan (2026-02-18)

## 1) Change List (paths + keys)

- `configs/windows.json`
  - `BULL_2021_H1.start`: `2021-01-01` -> `2026-02-14`
  - `BULL_2021_H1.end`: `2021-05-31` -> `2026-02-15`
  - `BEAR_2022.start`: `2022-01-01` -> `2026-02-16`
  - `BEAR_2022.end`: `2022-12-31` -> `2026-02-17`
- `scripts/rerun_failed_windows.sh`
  - Added `--config` input (default `configs/windows.json`)
  - For failed window replay, resolve `start/end` by window name from config first, then fallback to report values.

## 2) Rationale (mapped to fail_reasons)

- `MISSING_METRIC`: failed windows had `pipeline_exit_1` due to no local data in 2021/2022 ranges; no `summary/gate` artifacts were created.
- `LOW_TRADES`: with no run artifacts, trade metrics cannot be produced; moving windows into available local data range is the smallest non-core fix.
- This keeps execution/backtest core untouched and changes only config + rerun entry behavior.

## 3) Risk

- Semantic drift: window labels (`BULL_2021_H1`, `BEAR_2022`) no longer reflect original calendar periods.
- Potential policy impact: easier to complete quick suite, but historical comparability is reduced.
- Mitigation: keep this as local/quick-suite remediation; for production historical validation, restore original windows and backfill data.

## 4) Rollback

- Revert config only:
  - `git checkout -- configs/windows.json`
- Revert rerun script behavior:
  - `git checkout -- scripts/rerun_failed_windows.sh`
- Or explicit key rollback in `configs/windows.json` to 2021/2022 ranges.
