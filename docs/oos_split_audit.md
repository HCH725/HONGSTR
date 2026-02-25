# HONGSTR OOS Split Audit (R5-B)

## 1) Objective

Confirm whether IS/OOS/WF splits are hard-coded (fixed) and reproducible, and identify the source-of-truth.

## 2) Definitions

- **IS (in-sample)**: Historical data used for parameter optimization and model training.
- **OOS (out-of_sample)**: Data held back during optimization to verify the performance of selected parameters on unseen data.
- **WF (walkforward)**: A series of IS/OOS splits where the IS window expands or shifts, followed by a subsequent OOS test window.
- **"Hard-coded" means**: Exact date ranges or deterministic rule, not derived ad-hoc.

## 3) Source-of-truth (FOUND)

### Primary location(s)

The canonical boundary for the global IS/OOS split is **2024-12-31**.
**SSOT: [scripts/splits.py](file:///Users/hong/Projects/HONGSTR/scripts/splits.py)**

- **File(s)**:
  - `research/models/baseline.py`: `is_end="2024-12-31"`
  - `scripts/phase1_runner.py`: `IS_END = "2024-12-31"`, `OOS_START = "2025-01-01"`
  - `scripts/phase2_param_search.sh`: `IS_END="2024-12-31"`
  - `scripts/phase3_walkforward.sh`: `IS: ... -> 2024-12-31 | OOS: 2025-01-01 -> now`
- **Function(s)/constant(s)**: `IS_END`, `OOS_START`, `split_time_based()`.
- **Status**: **IDENTIFIED & CONSISTENT**.

### Secondary/derived references

- **configs/windows.json**: Contains window-specific ranges (e.g., NEUTRAL_2023, BULL_2024).
- **research/ML_README.md**: References `2025-01-01` as the start for research backtests.

## 4) Exact split ranges / rules (as implemented)

- **IS start**: `2020-01-01` (Standard across phase runners).
- **IS end**: `2024-12-31`.
- **OOS start**: `2025-01-01`.
- **OOS end**: `now` (Usually dynamic based on latest available data).
- **WF windowing rules**:
  - **WF1**: IS [2020-01-01 to 2022-12-31], OOS [2023-01-01 to 2023-12-31]
  - **WF2**: IS [2020-01-01 to 2023-12-31], OOS [2024-01-01 to 2024-12-31]
  - **WF3**: IS [2020-01-01 to 2024-12-31], OOS [2025-01-01 to now]

## 5) Evidence search

- **Keywords**: `in_sample`, `out_of_sample`, `oos`, `is`, `IS_END`, `OOS_START`.
- **Files searched**: `scripts/`, `research/`, `docs/`, `_local/`.
- **Commands used**: `rg -n "2024-12-31|2025-01-01" scripts/ research/`

## 6) How to verify (repro checklist)

- **Deterministic Splits**: Run `python3 research/models/baseline.py` (if configured with a dataset) or inspect `phase1_runner.py` constants.
- **Artifact Injection**: `scripts/build_model_artifact.sh` injects `'is_split_logic': '<= 2024-12-31 23:59:59 UTC'` into model metadata.
- **Backtest Outputs**: Inspect `window_meta.json` in any backtest run directory to confirm the `start` and `end` dates match the expected window from `configs/windows.json` or phase runners.

## 7) Recommendation (next minimal PR)

- **Canonical Configuration**: While `2024-12-31` is widely used, it is duplicated across several files.
- **Proposal**: Introduce a central `configs/research_splits.json` (or similar) to host these dates and have all scripts import from there. This ensures that when we roll forward to a new OOS year (e.g., 2026), we only change it in one place.
- **Docs Update**: Move this audit summary into a permanent `docs/research/splits.md` section in the prochain PR.
