# Regime Timeline Governance

## Overview

Market regime slicing allows Researchers to evaluate strategy performance under different market conditions (Bull/Bear/Sideways) without changing core execution logic.

## Single Source of Truth

- **Path**: `research/policy/regime_timeline.json`
- **Policy**: All backtest reporting and leaderboard analysis SHOULD use this file to determine time slices.

## Invariants

1. **End-Exclusive**: The `end_utc` timestamp is exclusive. If a regime ends at `12:00:00Z`, the next one can start at exactly `12:00:00Z`.
2. **Non-Overlapping**: No two regimes can occupy the same timestamp.
3. **Sorted**: Regimes in the JSON array MUST be sorted by `start_utc`.

## How to Adjust

1. Edit `research/policy/regime_timeline.json`.
2. Add a new object to the `regimes` array or adjust existing timestamps.
3. Ensure `rationale` provides a brief justification for the slice.

## How to Validate

Run the following command after any edits:

```bash
./.venv/bin/python -m pytest research/loop/tests/test_regime_timeline_policy.py
```

---
Safety Level: Governance (Docs Only)
