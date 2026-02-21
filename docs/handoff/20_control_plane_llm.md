# 20. Control-Plane Local LLM (Phase 0)

## Purpose

Phase 0 adds a **local control-plane advisor** for HONGSTR. It consumes event JSON and emits a strict machine-parseable decision artifact.

- Scope: diagnosis, summary, next tasks, safe remediation suggestions.
- Out of scope: running ETL/backtest/scheduling directly.

## Safety Model

1. **Allowlist-only actions** (`AllowedAction` enum):
   - `RUN_DAILY_ETL`
   - `RUN_WEEKLY_BACKFILL`
   - `RUN_RECOVER_DASHBOARD_FULL`
   - `RUN_HEALTHCHECK_DASHBOARD`
   - `RUN_CHECK_DATA_COVERAGE`
   - `RUN_TG_SANITY`
   - `OPEN_ISSUE_SUGGESTION`
2. No arbitrary shell execution from LLM output.
3. Unknown actions are rejected and converted into notes.
4. Secrets are redacted in event router output.

## Scheduler of Record

`launchd` remains the **scheduler-of-record**.

- LLM output is advisory only.
- Control-plane never mutates schedules or writes launchd configs.

## Failure Modes / Graceful Degradation

- If local LLM is disabled/unreachable, system falls back to `NullLLM`.
- If LLM output is malformed JSON, runner writes `status=FAIL` artifact.
- `scripts/control_plane_run.sh` always exits `0` (non-blocking).
- Optional Telegram WARN is best-effort only.

## Artifacts

- Event input: `data/events/latest_event.json`
- Decision JSON: `reports/control_plane_latest.json`
- Decision Markdown: `reports/control_plane_latest.md`

## Config

- `HONGSTR_LLM_MODE`: `null` (default), `ollama` (recommended), or `qwen`
- `HONGSTR_LLM_ENDPOINT`: endpoint URL
  - Ollama default: `http://127.0.0.1:11434`
- `HONGSTR_LLM_MODEL`: model id/name (for example `qwen2.5:7b`)

If mode endpoint is unreachable, runner falls back via `NullLLM` and continues non-blocking.

## Run

```bash
bash scripts/control_plane_run.sh
```

## Ops Integration (non-blocking)

`control_plane_run.sh` is invoked best-effort after:

- `scripts/daily_etl.sh`
- `scripts/backfill_1m_from_2020.sh`
- `scripts/recover_dashboard_full.sh`

These pipelines continue even if control-plane fails.
