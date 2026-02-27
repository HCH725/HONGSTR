> [!IMPORTANT] REFERENCE ONLY - Please see [Daily Report & Glossary](docs/ops/daily_report_zh.md) for current entry point.

# HONGSTR Autonomous Research Loop v1

## Purpose

The Autonomous Research Loop leverages the Reasoning Specialist (`deepseek-r1:7b`) to analyze system state and propose/run research experiments (backtests) to improve future model performance.

## Workflow

1. **Observe**: Read system snapshots (Freshness, Regime, ML Status).
2. **Propose**: Generate a JSON research proposal based on data anomalies or optimization gaps.
3. **Validate**: Cross-check the proposal against `research/experiments/registry.json`.
4. **Run**: Execute (simulated/report-only) backtests.
5. **Gate**: Evaluate with config-driven hard+soft governance policy.
6. **Report**: Generate markdown reports in `reports/research/`.
7. **Weekly Governance**: Generate report-only quant checklist artifacts under `reports/research/governance/`.

## Safety & Redlines

- **No Trading**: The loop is strictly inhibited from placing orders.
- **Allowlist Only**: Only strategies and symbols defined in `registry.json` are permitted.
- **Report Only**: Results are informational and do not automatically modify production weights.
- **Graceful Failure**: Any error results in a `WARN` log and exit code 0.

## Registry Configuration

Edit `research/experiments/registry.json` to modify:

- Allowed strategies and symbols.
- Parameter range constraints.
- Forbidden keywords (e.g. to prevent specific bias).

## Scheduling

The loop is intended to run daily at 06:20 via `launchd` (using `scripts/run_research_loop.sh`).

## Governance Standard

- Policy file: `research/policy/overfit_gates_aggressive.json`
- Candidate catalog: `research/policy/candidate_catalog.json`
- Ops docs: `docs/governance/overfit_gates_aggressive.md`
- Weekly checklist template: `docs/governance/overfit_weekly_checklist.md`
- Direction variants reporting: `docs/governance/direction_variants_reporting.md`
