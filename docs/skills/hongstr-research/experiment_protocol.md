# Experiment Protocol (IS/OOS / Walk-Forward / Gates / Leaderboards)

**MUST READ FIRST:** `docs/skills/global_red_lines.md`

## Fixed split (SSOT)
- IS/OOS split must be treated as a system SSOT constant.
- Do not hard-code dates in many places; reference the SSOT location (scripts/splits.py or equivalent).

## Walk-Forward variants
Define explicitly (use one and document it):
- **Standard WF:** rolling train window + rolling test window
- **Anchored WF:** expanding train window + rolling test window
- **Hybrid WF:** fixed warm-up + expanding train, etc. (must be documented)

## Gates
- Gates are **warn-only** by default (exit 0), unless explicitly called a “hard gate” in ops.
- Gate outputs must be traceable:
  - input manifest
  - computed metrics
  - thresholds used
  - decision (PASS/WARN/FAIL)
  - summary path(s)

## Candidate selection / leaderboard schema (minimum)
Every experiment should produce a leaderboard-like summary JSON with:
- experiment_id
- data range and split rules
- strategy name + params hash
- metrics: Sharpe, MDD, Return, Trades, WinRate (as applicable)
- gating decision and reasons
- artifacts pointers: summary_path, selection_path (if any), source_reason

## Reproducibility checklist
- Record exact run inputs:
  - symbols, timeframes, start/end
  - split constants version
  - research code version (git commit)
  - data snapshot timestamp (SSOT freshness)
- Never tune on OOS metrics; only evaluate on OOS after IS tuning is frozen.
