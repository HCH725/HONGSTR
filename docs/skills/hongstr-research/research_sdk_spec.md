# Research SDK Spec (Panel / Factor / Features / Labels)

**MUST READ FIRST:** `docs/skills/global_red_lines.md`

## Scope
- Research layer is **low-intrusion** and must remain **report_only** by default.
- Do not modify `src/hongstr/**`. Research artifacts must not change trading semantics.

## Core abstractions
### Panel
- A time-indexed panel representing OHLCV + derived signals at fixed frequencies (e.g., 1h/4h).
- Must be reproducible: every build has a manifest containing inputs, time range, timeframes, and versions.

### Factor
- A deterministic transform that maps a Panel -> factor series/features.
- Factors must be versioned and documented (name, params, dependencies, expected null handling).

### Features
- A feature table built from one or more factors.
- Must include:
  - feature list
  - normalization policy (if any)
  - alignment rules
  - manifest (hashes, time range, versions)

### Labels (optional)
- Labels are research-only targets (classification/regression), never used directly to execute trades.
- Must include:
  - label horizon definition
  - leakage constraints (strict shift / forward return)
  - manifest and reproducibility notes

## Leakage-avoidance checklist (non-negotiable)
1. **Time alignment**
   - Every feature at time `t` must only use information available at or before `t`.
2. **Shift discipline**
   - Labels must be shifted forward; features must never “peek” into future bars.
3. **Window boundaries**
   - Rolling windows must be causal (trailing), not centered.
4. **No cross-split contamination**
   - IS/OOS split must be fixed and applied before any tuning that can leak information.
5. **Walk-forward discipline**
   - Any walk-forward uses sequential training windows; never re-train on OOS.
6. **Artifact hygiene**
   - Do not commit generated parquet/pkl artifacts to git; store under runtime outputs or reports.

## Output expectations
- Outputs are: report markdown + small JSON summaries in SSOT if explicitly allowed.
- Default stance: report_only; no changes to pipeline execution or trading behavior.
