# HONGSTR Alert Artifact Skeleton v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / schema-first / read-only ingest design / no runtime wiring
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: alert artifact skeleton / central steward read-only ingest design
Plane: State Plane + Control Plane + Data Plane + Research/knowledge sidecar artifact contract
Expected SSOT/output impact: none

## 0. Purpose

This file defines the future read-only artifact skeleton for alert/state ingest.

The purpose is narrow:

- define which artifacts may exist
- define which component is allowed to produce them
- define which fields a future central steward may read
- prevent these artifacts from turning into a second writer or a second system-status calculator

This file does not create a new writer, a new Telegram path, or a new runtime queue.

## 1. Hard Red Lines

These rules apply to every artifact in this file:

- `scripts/state_snapshots.py` remains the only canonical writer for `data/state/*`
- `_local/telegram_cp/**` and any future central steward runtime may read these artifacts only; they must not rewrite them
- `alerts_latest.json` and `alerts_journal.jsonl` are read-only ingest artifacts, not top-level `/status` or `/daily` truth
- Obsidian / LanceDB outputs may appear as evidence or sidecar alerts only; they must not become `/status` or `/daily` truth
- `services_heartbeat.json` and `watchdog_status_latest.json` may expose component truth for their own scope, but they still do not authorize the steward to recompute `system_health_latest.json`
- no artifact in this file authorizes arbitrary repair, shell execution, or second-writer publication

## 2. Producer / Path Model

| Logical artifact | Repo-aligned path in v1 | Producer class | Writer boundary | Steward role |
|---|---|---|---|---|
| `alerts_latest.json` | recommended future path: `reports/state_atomic/alerts_latest.json` | atomic alert producer only | must stay outside `data/state/*` unless a later PR explicitly routes it through `scripts/state_snapshots.py` | read-only ingest |
| `alerts_journal.jsonl` | recommended future path: `reports/state_atomic/alerts_journal.jsonl` | atomic alert producer only | append-only atomic artifact; not canonical `data/state/*` | read-only ingest |
| `watchdog_status.json` | current repo-aligned paths: `reports/state_atomic/watchdog_status_latest.json` and canonical mirror `data/state/watchdog_status_latest.json` | control-plane watchdog producer plus canonical state writer mirror | atomic producer writes only under `reports/state_atomic`; only `scripts/state_snapshots.py` may mirror into `data/state/*` | read-only ingest |
| `services_heartbeat.json` | current repo-aligned path: `data/state/services_heartbeat.json` | canonical state writer | only `scripts/state_snapshots.py` | read-only ingest |

Notes:

- `watchdog_status.json` is the logical schema name in this document; the current repo uses the filename `watchdog_status_latest.json`
- `alerts_latest.json` and `alerts_journal.jsonl` are intentionally defined first as atomic producer artifacts so this PR cannot be mistaken for a second canonical state writer

## 3. Common Alert Record Fields

The common record shape below applies to:

- each entry under `alerts_latest.json`
- each line in `alerts_journal.jsonl`
- the top-level envelope of single-record artifacts such as `watchdog_status_latest.json`
- additive top-level metadata for `services_heartbeat.json`

| Field | Type | Producer-owned | Truth class | Rule |
|---|---|---|---|---|
| `ts_utc` | string | yes | event timestamp only | RFC 3339 / ISO 8601 UTC. |
| `source` | string | yes | provenance | Path, service label, or producer ID, for example `scripts/watchdog_status_snapshot.py` or `scripts/state_snapshots.py`. |
| `owner_plane` | string | yes | provenance | One of: `state_plane`, `control_plane`, `data_plane`, `research_plane`. |
| `severity` | string | yes | routing only | One of: `INFO`, `WARN`, `ERROR`, `CRITICAL`. Does not by itself define `/status` or `/daily`. |
| `alert_type` | string | yes | routing only | Stable machine-readable alert category, for example `watchdog_health`, `service_heartbeat_stale`, `ssot_input_missing`. |
| `summary` | string | yes | summary only | Human-readable short summary. Never a top-level truth source by itself. |
| `evidence_paths` | array[string] | yes | evidence only | Repo-relative paths to logs, docs, scripts, or artifacts supporting the alert. |
| `ssot_paths` | array[string] | yes | truth pointer | Repo-relative canonical or atomic paths the steward is allowed to read. |
| `next_action` | string | yes | routing only | Controlled next step such as `none`, `run_refresh_state`, `request_manual_review`, `send_telegram_alert`. |
| `dedupe_key` | string | yes | delivery control only | Stable duplicate key for same alert meaning. |
| `cooldown_key` | string | yes | delivery control only | Stable suppression bucket for repeated alerts. |
| `recovery_of` | string or null | yes | delivery control only | References the prior `dedupe_key` or event identifier being recovered. |
| `escalation_target` | string | yes | routing only | Expected destination such as `telegram_central_steward`, `human_operator`, `none`. |
| `repair_class` | string or null | yes | routing only | Expected policy class such as `record_only`, `telegram_notify`, `bounded_repair`, `manual_review`, `forbidden`. |

Recommended additive field:

- `event_id`: strongly recommended when the artifact is journaled or cross-linked to `docs/architecture/agent_event_schema_v1.md`

## 4. Truth-Bearing vs Summary-Only Boundary

### 4.1 Fields that producers may emit and the steward may trust as provenance or pointers

These fields may be emitted by the SSOT writer or an atomic producer:

- `ts_utc`
- `source`
- `owner_plane`
- `evidence_paths`
- `ssot_paths`
- domain payload fields such as `services`, `status`, `status_reason`, `launchctl`, `last_check`

### 4.2 Fields that producers may emit but that must never become `/status` or `/daily` truth by themselves

These fields are allowed for alerting and routing, but are not top-level truth:

- `severity`
- `alert_type`
- `summary`
- `next_action`
- `dedupe_key`
- `cooldown_key`
- `recovery_of`
- `escalation_target`
- `repair_class`

Interpretation rule:

- `/status` and `/daily` truth still comes from canonical SSOT artifacts such as `data/state/system_health_latest.json` and `data/state/daily_report_latest.json`
- alert artifacts may point to SSOT, summarize SSOT, or summarize atomic producer output, but they may not overwrite or replace top-level SSOT

### 4.3 Steward-only derived fields that must stay out of producer truth

If a future central steward needs any of the following, they must remain delivery-local and non-authoritative:

- rendered Telegram text
- delivery attempt count
- last delivered timestamp
- local suppression cache state
- human annotation added after ingest

These are not part of the canonical producer contract in v1.

## 5. Artifact Skeletons

## 5.1 `alerts_latest.json`

Recommended role:

- most recent alert snapshot for read-only ingest
- non-canonical summary surface
- may aggregate multiple planes, but only as alert entries, not as recomputed system truth

Recommended wrapper schema:

```json
{
  "schema_version": "alerts_latest.v1",
  "generated_utc": "2026-03-06T12:00:00Z",
  "source": "reports/state_atomic/alerts_latest.json",
  "owner_plane": "state_plane",
  "alerts": [
    {
      "event_id": "aev1_01JX...",
      "ts_utc": "2026-03-06T11:59:58Z",
      "source": "scripts/watchdog_status_snapshot.py",
      "owner_plane": "control_plane",
      "severity": "WARN",
      "alert_type": "watchdog_health",
      "summary": "tg_cp watchdog log is stale beyond the expected interval.",
      "evidence_paths": [
        "scripts/watchdog_status_snapshot.py",
        "reports/state_atomic/watchdog_status_latest.json"
      ],
      "ssot_paths": [
        "data/state/watchdog_status_latest.json",
        "data/state/system_health_latest.json"
      ],
      "next_action": "send_telegram_alert",
      "dedupe_key": "watchdog_health:tg_cp_watchdog:stale",
      "cooldown_key": "watchdog_health:control_plane",
      "recovery_of": null,
      "escalation_target": "telegram_central_steward",
      "repair_class": "telegram_notify"
    }
  ]
}
```

Rules:

- `alerts[]` entries own the common alert fields
- wrapper-level `source` and `owner_plane` describe the file producer, not the alerted subsystem
- the steward may read `alerts[]`, but may not treat the wrapper as a replacement for `system_health_latest.json`

## 5.2 `alerts_journal.jsonl`

Recommended role:

- append-only alert journal
- read-only history for dedupe, cooldown, and recovery correlation
- never a second canonical state writer

Recommended line schema:

```json
{
  "event_id": "aev1_01JX...",
  "ts_utc": "2026-03-06T11:59:58Z",
  "source": "scripts/watchdog_status_snapshot.py",
  "owner_plane": "control_plane",
  "severity": "WARN",
  "alert_type": "watchdog_health",
  "summary": "tg_cp watchdog log is stale beyond the expected interval.",
  "evidence_paths": [
    "reports/state_atomic/watchdog_status_latest.json"
  ],
  "ssot_paths": [
    "data/state/watchdog_status_latest.json"
  ],
  "next_action": "send_telegram_alert",
  "dedupe_key": "watchdog_health:tg_cp_watchdog:stale",
  "cooldown_key": "watchdog_health:control_plane",
  "recovery_of": null,
  "escalation_target": "telegram_central_steward",
  "repair_class": "telegram_notify"
}
```

Rules:

- one line equals one alert emission or one recovery emission
- a recovery line sets `recovery_of` to the prior active alert key
- journal lines may be read for history, but cannot override current canonical SSOT

## 5.3 `watchdog_status.json` logical schema

Current repo-aligned artifacts:

- atomic producer: `reports/state_atomic/watchdog_status_latest.json`
- canonical mirror: `data/state/watchdog_status_latest.json`

Current existing domain payload already includes:

- `schema_version`
- `generated_utc`
- `ts_utc`
- `label`
- `launchctl_target`
- `status`
- `status_reason`
- `launchctl`
- `last_check`
- `sources`

Recommended additive alert/read-only ingest fields:

```json
{
  "schema_version": "watchdog_status.v1",
  "generated_utc": "2026-03-06T12:00:00Z",
  "ts_utc": "2026-03-06T12:00:00Z",
  "source": "scripts/watchdog_status_snapshot.py",
  "owner_plane": "control_plane",
  "severity": "WARN",
  "alert_type": "watchdog_health",
  "summary": "tg_cp watchdog is loaded but the last check log is stale.",
  "evidence_paths": [
    "scripts/watchdog_status_snapshot.py",
    "reports/state_atomic/watchdog_status_latest.json"
  ],
  "ssot_paths": [
    "reports/state_atomic/watchdog_status_latest.json",
    "data/state/watchdog_status_latest.json"
  ],
  "next_action": "send_telegram_alert",
  "dedupe_key": "watchdog_health:tg_cp_watchdog:log_stale",
  "cooldown_key": "watchdog_health:control_plane",
  "recovery_of": null,
  "escalation_target": "telegram_central_steward",
  "repair_class": "telegram_notify",
  "label": "com.hongstr.tg_cp_watchdog",
  "launchctl_target": "gui/501/com.hongstr.tg_cp_watchdog",
  "status": "WARN",
  "status_reason": "log_stale>600s",
  "launchctl": {
    "ok": true
  },
  "last_check": {
    "exists": true,
    "line_status": "WARN"
  },
  "sources": {
    "output_path": "reports/state_atomic/watchdog_status_latest.json"
  }
}
```

Alignment rule:

- the existing watchdog payload stays authoritative for watchdog scope
- added alert fields are metadata for steward ingest only
- the steward may summarize watchdog status, but must not recompute top-level `system_health_latest.json`

## 5.4 `services_heartbeat.json`

Current repo-aligned canonical artifact:

- `data/state/services_heartbeat.json`

Current existing domain payload already includes:

- `generated_utc`
- `services`

Current consumer compatibility notes:

- `scripts/tg_cp_healthcheck.py` accepts `ts_utc` or `generated_utc`
- `web/app/api/status/route.ts` already supports the current map format: `{"services": {"name": {"status": ...}}}`

Recommended additive schema:

```json
{
  "schema_version": "services_heartbeat.v1",
  "generated_utc": "2026-03-06T12:00:00Z",
  "ts_utc": "2026-03-06T12:00:00Z",
  "source": "scripts/state_snapshots.py",
  "owner_plane": "state_plane",
  "severity": "INFO",
  "alert_type": "services_heartbeat_snapshot",
  "summary": "Latest service heartbeat snapshot for read-only consumers.",
  "evidence_paths": [
    "scripts/state_snapshots.py"
  ],
  "ssot_paths": [
    "data/state/services_heartbeat.json"
  ],
  "next_action": "none",
  "dedupe_key": "services_heartbeat:latest",
  "cooldown_key": "services_heartbeat:state_plane",
  "recovery_of": null,
  "escalation_target": "none",
  "repair_class": "record_only",
  "services": {
    "tg_cp": {
      "status": "ALIVE",
      "log_path": "logs/launchd_tg_cp.out.log",
      "age_h": 0.1,
      "last_heartbeat_utc": "2026-03-06T11:54:00Z"
    }
  }
}
```

Alignment rule:

- preserve the existing `services` object-map shape
- keep `generated_utc` for backward compatibility
- add `ts_utc` in future only as a compatibility-safe alias, not as a schema replacement
- `services_heartbeat.json` may inform service freshness, but it still does not authorize the steward to replace `system_health_latest.json`

## 6. Responsibility Boundary

Producer responsibility:

- emit stable artifact shape
- own `dedupe_key`, `cooldown_key`, `recovery_of`, `repair_class`, and `escalation_target`
- provide concrete `evidence_paths` and `ssot_paths`

Central steward responsibility:

- read these artifacts only
- suppress duplicate notifications using producer-provided keys
- send recovery notice only when a producer explicitly marks recovery or a later canonical artifact clearly supersedes the same alert scope

Forbidden for the steward:

- rewriting artifacts
- collapsing `alerts_latest.json` into a new top-level system status
- promoting research/knowledge sidecar alerts into `/status` or `/daily` truth

## 7. Degrade / Kill Switch / Incremental Adoption

Degrade:

- if an artifact is missing or unreadable, the steward must fall back to existing canonical SSOT behavior
- missing alert artifacts do not justify live API recomputation for P0 status

Kill switch:

- do not wire these schemas into runtime yet
- revert the docs commit or close the stacked PR if field names need revision

Suggested follow-on adoption path:

1. docs/tests-only validation for artifact shape
2. optional manual producer helper may emit `alerts_latest.json` and `alerts_journal.jsonl` only under `reports/state_atomic/*`; it must stay stoppable and outside the P0 path
   Current invocation decision: keep the helper manual-only and out of schedule; see `docs/architecture/atomic_alert_producer_invocation_decision_v1.md`.
3. optional canonical mirror only through `scripts/state_snapshots.py`, if later approved
4. central steward read-only ingest only after Stage 2 / Stage 7 guardrails remain green
