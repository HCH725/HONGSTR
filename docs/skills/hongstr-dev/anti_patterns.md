# Anti-patterns (Engineering)

Policy SSOT: `docs/skills/global_red_lines.md`

- Treating tg_cp/dashboard top-level status as a compute layer (derived/log/artifact fallback scans).
- Letting non-canonical jobs write `data/state/*` directly.
- Assigning independent State Plane ownership to `daily_healthcheck`.
- Using `python` from `PATH` instead of `./.venv/bin/python`.
- Re-stating guardrails inconsistently across docs instead of referencing policy SSOT.
- Combining unrelated refactors and fixes in one PR.
