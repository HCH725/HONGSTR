Assembled System Examples (docs-only)

Example A: qwen2.5-coder:7b-instruct
- base_system_prompt
- overlay_qwen2.5-coder_7b_instruct
- skills: status_overview, freshness_3x3
- ssot snapshot: system_health_latest.json (short)
- blocks: STATUS, FRESHNESS

Example B: qwen2.5:7b-instruct
- base_system_prompt
- overlay_deepseek-r1_7b
- skills: status_overview
- ssot snapshot: regime_monitor_latest.json (short)

Example C: qwen2.5:7b-instruct
- base_system_prompt
- overlay_qwen2.5_7b_instruct
- skills: status_overview
- ssot snapshot: system_health_latest.json (short)
- blocks: STATUS
