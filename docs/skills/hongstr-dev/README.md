# hongstr-dev (Skill Pack)

Audience: coding agents modifying this repository and delivering changes via GitHub PRs.

Policy SSOT: `docs/skills/global_red_lines.md` (all guardrails come from this file).

## Current canonical architecture
- State Plane owner: `com.hongstr.refresh_state` is the canonical scheduler for SSOT publication.
- Legacy alias: `com.hongstr.daily_healthcheck` runs at `02:30` as a compatibility trigger only; it has no independent state ownership.
- Writer boundary: only `scripts/state_snapshots.py` writes canonical `data/state/*` snapshots.
- Consumer boundary: tg_cp and dashboard top-level status are SSOT-only readers.
  - No derived/log/artifact scanning for top-level status.
  - Missing/unreadable SSOT must degrade to `UNKNOWN` + `refresh_hint` (`bash scripts/refresh_state.sh`).
- Runtime invariant: always use `./.venv/bin/python` (do not assume `python` exists on `PATH`).

## This pack
- `repo_inventory.md`: ownership and boundaries (core/state/control).
- `ops_runbook.md`: launchd + SSOT refresh operational SOP.
- `pr_ssot_flow.md`: branch/commit/PR flow under GitHub SSOT.
- `testing_verification.md`: required checks before PR.
- `anti_patterns.md`: common mistakes to avoid.
- Canonical schema reference: `docs/skills/skill_specs/skill_specs_v1.md`.
