> [!IMPORTANT] REFERENCE ONLY - Please see [Daily Report & Glossary](docs/ops/daily_report_zh.md) for current entry point.

# Telegram Operator Manual (HONGSTR)

## 1. Skill Discovery & Help

Use `/skills` to see all available read-only skills.

- **Check Detailed Help**: `/skills help <skill_name>`
  - *Example*: `/skills help status_overview`
  - *Output*: Displays description, parameters (必填/預設), and example command.

- **Check Technical Schema**: `/run help <skill_name>`
  - *Example*: `/run help signal_leakage_audit`
  - *Output*: Displays raw schema, allowed keys, and JSON example.

## 2. Running Audits & Monitoring

- **System Status**: `/status` (or `/run status_overview`)
- **System Health Brief**: `/run system_health_morning_brief env=prod`
- **Strategy Leakage Audit**: `/run signal_leakage_and_lookahead_audit backtest_id="BT_123"`

## 3. Recommended Operator Flow

1. **Verify State**: Start with `/status` to ensure SSOT is OK.
2. **Review Pool**: Use `/skills help strategy_pool_summary` to see current candidates.
3. **Audit Candidate**: Run `/run help <audit_skill>` to understand parameters, then execute the audit.

---
*Safety Statement: core diff=0 | no-exec | report_only*

