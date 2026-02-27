> [!IMPORTANT] REFERENCE ONLY - Please see [Daily Report & Glossary](docs/ops/daily_report_zh.md) for current entry point.

# DCA-1 Cost-Aware Research Executor (Report-Only)

> REFERENCE ONLY


This module is research-only and does not change production trading behavior.

## Files

- `research/loop/dca_cost_model.py`
- `research/loop/dca1_executor.py`

## Slippage Fallback

1. `L1_ORDERBOOK_IMPACT`
2. `L2_SPREAD_VOL`
3. `L3_FIXED_BPS`

Each artifact includes:

- `fee_bps`
- `slippage_bps`
- `total_cost_bps`
- `slippage_source`
- `fee_scenario`

## Fee Scenarios

- `standard`
- `vip`
- `stress` (2x baseline fee)

## Stress Gate

DCA gate includes a cost stress check:

- `stress_total_cost_bps <= max_cost_bps`
- `stress_cost / standard_cost <= max_cost_multiplier`

## Sweep

`run_dca1_sweep(...)` sweeps:

- `safety_multiplier`
- `safety_gap_bps`
- fee scenarios

Output remains report-only and comparable via summary/gate/selection/report artifacts.
