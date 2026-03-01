# Skill: status_overview

id: status_overview
title: SSOT Status Overview
purpose: Provide a concise health/status view based on SSOT JSON files under data/state/.
inputs:
- none
outputs:
- markdown block "STATUS" with ssot_status, key timestamps, and hints
constraints:
- read-only; must not execute shell; must not infer beyond SSOT
ssot_sources:
- data/state/system_health_latest.json
- data/state/services_heartbeat.json
- data/state/execution_mode.json
examples:
- "Show current system status"
