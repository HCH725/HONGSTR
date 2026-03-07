---
trigger: always_on
---

# HONGSTR Guardrails (Must Follow)

## DO NOT MODIFY

- `src/hongstr/**` (core engine: backtest/execution/matching semantics)
- Any code that can place orders / trade / change account state

## ALLOWED TO MODIFY

- `research/**` (research SDK, features/labels/models/signals; report_only only)
- `_local/**` (tg_cp central steward; read-only; no repo writes)
- `docs/**`
- `scripts/**` ONLY if it does not change production semantics.
  - Do not change ETL/launchd/trading behavior unless explicitly instructed.

## LINEAR-FIRST INTAKE

- Formal HONGSTR execution starts only after a matching Linear item exists.
- Sandbox work also requires Linear tracking. No orphan work.
- `Codex` and `antigravity` must stop and treat the task as intake first if no matching Linear item exists yet.
- Every tracked item must close as `DONE`, `REJECT`, `DEFERRED`, `SANDBOX ONLY`, or `MERGED / SUPERSEDED`.
- Canonical policy lives in `AGENTS.md` under `Linear-first governance (required)`.

## REQUIRED CHECKS BEFORE OPENING A PR

- Core diff must be zero:
  - `git diff origin/main...HEAD -- src/hongstr | wc -l` => must be `0`

- No artifacts tracked by git:
  - `git ls-files | rg '\.(parquet|pkl)$'` => must be empty

- PR must include:
  - Safety statement (what cannot happen)
  - Rollback instructions (how to revert)
