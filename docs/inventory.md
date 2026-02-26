# HONGSTR Repository Inventory (v1)

> Purpose: A single index of key entrypoints, artifacts, and operational flows.
> Guardrails: core engine under src/hongstr/** must remain unchanged (core diff=0).

## Operations (launchd)

- ops/launchagents/*.plist
  - dashboard: com.hongstr.dashboard
  - daily_etl: com.hongstr.daily_etl
  - weekly_backfill: com.hongstr.weekly_backfill

## Data Pipeline

- scripts/daily_etl.sh
- scripts/backfill_1m_from_2020.sh
- scripts/ingest_historical.py
- scripts/aggregate_data.py
- scripts/check_data_coverage.sh
- data/derived/SYMBOL/1m/klines.jsonl (canonical backtest source)

## Notifications

- scripts/notify_telegram.sh (non-blocking)
- scripts/load_env.sh (.env loader)

## Dashboard

- scripts/dashboard.py
- URL: <http://127.0.0.1:8501>

## Guardrails / Governance

- scripts/guardrail_check.sh
- .github/CODEOWNERS
- .github/workflows/guardrails.yml
- .github/pull_request_template.md

## Governance (Overfit)

- [Overfit Governance Standard (Aggressive)](docs/governance/overfit_governance_aggressive.md)
- [Overfit Weekly Report Template](docs/governance/overfit_weekly_report_template.md)

## State / Artifacts (expected)

- data/state/* (freshness/regime/selection/etc)
- data/backtests/*/*/summary.json (and related artifacts)
