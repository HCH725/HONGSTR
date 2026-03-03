# HONGSTR Ollama Prompt/Skill Pack (v1)

Goal: make all Ollama models follow the same engineering-grade operating procedure ("engineering learning"), improving completeness, consistency, and safety without changing model weights.

Models:
- qwen2.5-coder:7b-instruct (coding-focused, proposal-first)
- deepseek-r1:7b (reasoning specialist)
- qwen2.5:7b-instruct (ops/partner-friendly)

This pack is **spec-first** in v1: it defines contracts and templates, and tg_cp may inject the prompt files directly at runtime. Dispatcher wiring is a later PR.

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

Runtime note:
- tg_cp prepends base_system_prompt + model overlay + injection_contract when TG_PROMPT_PACK_ENABLED is not 0 (default 1).
