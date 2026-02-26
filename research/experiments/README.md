# Research Experiments

This directory is intended for iterative strategy validation, Jupyter notebooks, ML model training, and custom parameter optimization scripts that consume the `reports/research/features/` artifacts.

## Usage Guidelines

1. Scripts here should strictly **READ** from `reports/research/features/*.parquet` and `reports/research/panels/*.parquet`.
2. Do not re-invent data engineering logic here. If a new feature is needed, add it to `research/factors/` and rebuild the artifacts.
3. Store temporary experiment outputs (like plots, ML weights) in `reports/strategy_research/` or `reports/research/_failed/`. Do not pollute the core repo with binaries.

## Phase-2 report_only candidates

PR-1 adds a research-only candidate catalog and artifact writer:

- `research/experiments/candidate_catalog.py`
- `research/experiments/report_only_artifacts.py`

The writer emits per-candidate `summary.json`, `gate.json`, `selection.json`,
and `*_results.json` under `reports/research/<run_id>/...` for leaderboard /
strategy-pool style ranking without touching `src/hongstr/**`.
