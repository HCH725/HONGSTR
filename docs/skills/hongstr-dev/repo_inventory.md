# Repo Inventory (Dev)

Policy SSOT: `docs/skills/global_red_lines.md`

## Core (stability-first)
- `src/hongstr/**` is core engine scope and must remain unchanged for slimdown/ops/docs work.

## State Plane (canonical SSOT publication)
- Orchestrator: `scripts/refresh_state.sh`
- Canonical writer: `scripts/state_snapshots.py`
- Canonical runtime outputs (untracked): `data/state/*.json`

### Atomic producers (non-canonical outputs)
- Atomic/intermediate producers should write under `reports/state_atomic/*`.
- Canonical snapshots are published only through `scripts/state_snapshots.py`.

## Control Plane (SSOT-only consumers)
- `_local/telegram_cp/` (`tg_cp_server.py`): read-only status/control interface.
- `web/` dashboard/API status endpoints: read-only SSOT consumption for top-level status.
- Top-level status must not be derived from logs/artifacts/derived scans.

## Launchd ownership (3-plane summary)
- Data Plane: ETL/backfill/retention/backtest jobs.
- State Plane: `com.hongstr.refresh_state` (canonical), `com.hongstr.daily_healthcheck` (alias/deprecation path only).
- Control Plane: dashboard/tg_cp/realtime_ws/research queue control.

See also: `docs/slimdown_launchd_planes.md`.
