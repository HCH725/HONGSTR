# Artifacts & Traceability Rules (Research)

**MUST READ FIRST:** `docs/skills/global_red_lines.md`

## Where outputs go
- Human-readable reports: `reports/research/`
- Small state summaries (if allowed): `data/state/*.json` (runtime only; do not commit)

## Naming conventions
- `reports/research/EXP_<yyyymmdd_hhmm>_<topic>/report.md`
- `reports/research/EXP_<...>/manifest.json`
- `reports/research/EXP_<...>/leaderboard.json`

## Manifest requirements (minimum)
manifest.json should include:
- experiment_id
- created_utc
- git_commit
- symbols/timeframes
- split constants (IS_END_DATE, OOS_START_DATE) + source path
- SSOT input timestamps (freshness_table ts_utc, coverage_matrix ts_utc)
- parameters (and param hashes)

## Pointers in summaries
When a JSON summary references computed results:
- Always include:
  - `summary_path`
  - `source_reason` (e.g., "full_runs" vs "fallback_fragment")
  - `inputs` (hashes/versions)
- Never reference or require committed parquet/pkl.
