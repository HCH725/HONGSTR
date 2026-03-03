---
name: hongstr-ssot-only
description: For any system status questions, read SSOT JSONs on disk; do not recompute or infer missing state.
compatibility: opencode
---

## Principle
- When asked about **system status/health/freshness/coverage/brake/regime/daily**, ALWAYS read SSOT files.
- Do NOT generate new SSOT outputs. Do NOT "recompute" metrics in-chat.

## SSOT files (read-only)
- data/state/system_health_latest.json
- data/state/freshness_table.json
- data/state/coverage_matrix_latest.json
- data/state/brake_health_latest.json
- data/state/regime_monitor_latest.json
- data/state/daily_report_latest.json

## Required output format
1) What you checked (exact file paths)
2) Commands (copy-paste)
3) Key lines to paste back
