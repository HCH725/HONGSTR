# HONGSTR Ollama Prompt/Skill Pack (v1)

Goal: make all Ollama models follow the same engineering-grade operating procedure ("engineering learning"), improving completeness, consistency, and safety without changing model weights.

Models:
- qwen2.5-coder:7b-instruct (coding-focused, proposal-first)
- deepseek-r1:7b (reasoning specialist)
- qwen2.5:7b-instruct (ops/partner-friendly)

This pack is **docs-only** in v1: it defines contracts and templates. Runtime injection (tg_cp / dispatcher) is a later PR.

Contents:
- base_system.md: global mission + red lines + procedure + output contract
- overlays/: per-model overlays (coder / reasoner / ops)
- skills/: skills registry schema + example skills (read-only)
- blocks/: stable markdown blocks spec for reports (status/freshness/regime/daily)
- specs/: caching, context assembly, and governance rules

Non-negotiables:
- core diff=0 for src/hongstr
- tg_cp strictly read-only/no-exec
- ML/Research report_only
- no data/** artifacts committed
- GitHub PR-based governance
