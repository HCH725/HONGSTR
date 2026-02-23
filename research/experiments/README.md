# Research Experiments

This directory is intended for iterative strategy validation, Jupyter notebooks, ML model training, and custom parameter optimization scripts that consume the `reports/research/features/` artifacts.

## Usage Guidelines

1. Scripts here should strictly **READ** from `reports/research/features/*.parquet` and `reports/research/panels/*.parquet`.
2. Do not re-invent data engineering logic here. If a new feature is needed, add it to `research/factors/` and rebuild the artifacts.
3. Store temporary experiment outputs (like plots, ML weights) in `reports/strategy_research/` or `reports/research/_failed/`. Do not pollute the core repo with binaries.
