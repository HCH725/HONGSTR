---
description: HONGSTR Core Boundaries & Red Lines
---

# HONGSTR Core Boundaries

**Role**: You are a bounded auxiliary agent working within the HONGSTR repository.

## Red Lines (HARD STOP)

If your task touches any of the following, you MUST stop immediately and hand off to Codex:

1. **Core Engine**: No modifications to `src/hongstr/**` (backtest, execution, matching semantics, trading logic).
2. **State Writers**: No modifications to state writer or producer semantics.
3. **Critical Scripts**:
   - DO NOT modify `scripts/refresh_state.sh`
   - DO NOT modify `scripts/state_snapshots.py`
4. **Control Plane**: No modifications to `tg_cp` runtime boundaries or UI logic.
5. **Execution/Safety**: No modifications to any trading, execution, or safety-critical paths.
6. **Secrets & Config**:
   - DO NOT modify `.env` structure, key naming, or secrets loading mechanisms.
   - NEVER output, leak, or print any secrets/keys.
7. **Refactoring**: No large-scale refactoring of any components.

## Allowed Scope (Sandbox / Docs-First)

- Read-only analysis and PR review support.
- Docs-first / schema-first / governance-first updates.
- Modifications limited ONLY to `.agent/**`, `AGENTS.md`, `docs/**`, non-core tests, and non-core documentation tooling.

## Enforcement

If a request is ambiguous or broad, or if you suspect it might step over these boundaries, STOP. Output a handoff note for Codex. Do not attempt to guess or bypass these restrictions.
