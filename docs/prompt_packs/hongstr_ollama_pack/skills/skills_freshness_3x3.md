# Skill: freshness_3x3

id: freshness_3x3
title: Freshness 3x3
purpose: Summarize data freshness using SSOT freshness_table.json thresholds and rows.
inputs:
- none
outputs:
- markdown block "FRESHNESS" (3x3 summary)
constraints:
- read-only; prefer SSOT as single source of truth
ssot_sources:
- data/state/freshness_table.json
examples:
- "Show freshness table summary"
