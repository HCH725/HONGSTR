# Skill Spec: backtest_reproducibility_audit

## Objective

Verify that a backtest result can be reproduced between a baseline SHA (working tree) and the research manifest.

## SSOT Requirement

Expects a `*reproducibility.json` artifact in `reports/research/` containing:

- `baseline_sha`
- `metrics_delta`
- `environment_checksum`

## Current Status (PR-B)

SKELETON. Returns `UNKNOWN` if artifacts are missing.

- **Guidance**: Ensure the backtest reproducibility producer is active.
