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

## Architecture

- [System Flow & Terminology Glossary](docs/architecture/flow_and_glossary.md)

## Operations (Partner & Operator)

- [Daily Report Single Entry](docs/ops/daily_report_single_entry.md) **(Primary)**
- [Daily Report & Glossary (zh-TW)](docs/ops/daily_report_zh.md) **(Reference)**
- [Telegram Operator Manual](docs/ops/telegram_operator_manual.md) **(Reference)**
- [Daily Report Contract](docs/ops/daily_report_contract.md) **(Reference)**
- [Acronym Glossary (zh-TW)](docs/ops/acronym_glossary_zh.md)

## PM / Audit References (Reference)

These are reference materials, not daily operational entrypoints. Daily status should be consumed from `/daily` only.

- [PM Checklist](docs/ops/pm_checklist.md)
- [PM Snapshot Runbook](docs/ops/pm_snapshot_runbook.md)
- `docs/audits/*.md` (historical analysis reports, reference-only)
- `docs/governance/*.md` (weekly governance and policy background, reference-only)
- `docs/runbook/*.md` (operational fallback manual, reference-only)

## State / Artifacts (expected)

- data/state/* (freshness/regime/selection/etc)
- data/backtests/*/*/summary.json (and related artifacts)
