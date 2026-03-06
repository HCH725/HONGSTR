# HONGSTR Central Steward Read-Only Ingest v1

Last updated: 2026-03-06 (UTC+8)
Status: policy-first / read-only ingest design with disabled-by-default shadow prototype
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: alert artifact skeleton / central steward read-only ingest design
Plane: Central steward read-only reporting boundary
Expected SSOT/output impact: none

## 0. Purpose

This file defines how the future central steward may read alert/state artifacts without becoming:

- a second canonical writer
- a second system-status calculator
- a free-form repair executor

The design target is narrow:

- read canonical SSOT and approved atomic producer artifacts
- dedupe and cooldown delivery
- send recovery or summary notifications through Telegram
- never recompute top-level truth

## 1. Producer / Consumer Boundary

| Artifact family | Typical path | Producer | Steward permission | Truth class |
|---|---|---|---|---|
| top-level SSOT | `data/state/system_health_latest.json`, `data/state/daily_report_latest.json` | `scripts/refresh_state.sh` -> `scripts/state_snapshots.py` | read-only | canonical top-level truth |
| canonical component SSOT | `data/state/services_heartbeat.json`, `data/state/watchdog_status_latest.json` | `scripts/state_snapshots.py` | read-only | canonical component truth |
| atomic control-plane health | `reports/state_atomic/watchdog_status_latest.json` | `scripts/watchdog_status_snapshot.py` | read-only | atomic producer truth for watchdog scope |
| future atomic alert artifacts | `reports/state_atomic/alerts_latest.json`, `reports/state_atomic/alerts_journal.jsonl` | atomic producer only | read-only | alert/routing ingest only |
| research / knowledge sidecar artifacts | report or retrieval artifacts under approved sidecar paths | report-only / sidecar producer | read-only | summary-only, never top-level truth |

Boundary rule:

- if an artifact lives under `data/state/*`, only the canonical state writer may create or update it
- if an artifact lives under `reports/state_atomic/*`, it may be produced atomically for ingest, but it still does not authorize the steward to publish new canonical truth

## 2. Steward Ingest Order

The future central steward should ingest in this order:

1. top-level SSOT:
   - `data/state/system_health_latest.json`
   - `data/state/daily_report_latest.json`
2. component truth and health detail:
   - `data/state/services_heartbeat.json`
   - `data/state/watchdog_status_latest.json`
3. non-canonical alert artifacts:
   - `reports/state_atomic/alerts_latest.json`
   - `reports/state_atomic/alerts_journal.jsonl`
4. report-only sidecar artifacts:
   - research or knowledge outputs that are already approved as non-authoritative

Interpretation rule:

- if top-level SSOT exists, it wins
- if top-level SSOT is missing, unreadable, or stale, the steward may report `UNKNOWN` and the existing `refresh_hint`
- the steward must not synthesize a new top-level status by combining lower-level artifacts on its own

## 3. What The Steward May Do

The steward may do only these read-only ingest operations:

- parse approved artifacts
- dedupe repeated alerts by `dedupe_key`
- apply notification cooldown by `cooldown_key`
- emit one recovery notice when a producer marks `recovery_of`
- merge multiple alert summaries into one Telegram message
- prefer canonical `ssot_paths` when linking evidence in Telegram output

These are formatting and delivery operations, not state recomputation.

## 4. What The Steward Must Not Do

The steward must not:

- recompute `system_health_latest.json`
- recompute `/daily` from raw component files when canonical `daily_report_latest.json` already exists
- call live external APIs as a P0 dependency for `/status` or `/daily`
- invent new `severity`, `repair_class`, or `escalation_target` values that are not producer-provided or canonically documented
- run arbitrary shell commands
- open arbitrary repairs or self-heal flows
- write back into `data/state/*`
- treat Obsidian / LanceDB outputs as top-level truth

## 5. Responsibility Boundary For Dedupe / Cooldown / Recovery

| Concern | Producer responsibility | Steward responsibility | Forbidden behavior |
|---|---|---|---|
| `dedupe_key` | emit a stable duplicate key | suppress duplicate outward alerts | invent a new canonical key that overrides producer meaning |
| `cooldown_key` | emit a stable cooldown bucket | rate-limit repeated Telegram alerts | store cooldown as canonical SSOT |
| `recovery_of` | point to the prior alert being recovered | send one recovery notice if operator-visible alert existed | declare recovery without clear producer evidence |
| `summary` | emit concise alert text | format or shorten for Telegram | turn summary prose into top-level SSOT |
| `ssot_paths` | point to canonical or approved atomic evidence | use links/pointers in output | replace those paths with live API results |

Implementation note:

- any future steward-side suppression cache must stay delivery-local and non-authoritative
- if that cache is absent or lost, the system should degrade to a repeated summary, not to invented state

## 6. Plane-Specific Ingest Rules

### 6.1 State Plane

Allowed steward input:

- `data/state/system_health_latest.json`
- `data/state/daily_report_latest.json`
- `data/state/services_heartbeat.json`

Rules:

- these are the primary P0 inputs
- steward may summarize them
- steward must not re-collapse component status into a replacement `ssot_status`

### 6.2 Control Plane Health / Watchdog

Allowed steward input:

- `reports/state_atomic/watchdog_status_latest.json`
- `data/state/watchdog_status_latest.json`

Rules:

- watchdog artifacts may trigger alerts or recovery notices
- the canonical mirror under `data/state/*` is preferred when both exist
- watchdog health does not authorize the steward to rewrite top-level system state

### 6.3 Data Plane Freshness / Coverage

Allowed steward input:

- only through canonical SSOT artifacts or approved alert artifacts that point back to canonical SSOT paths

Rules:

- freshness and coverage may affect system status only through the state writer
- the steward may report them only as read-only consequences of canonical artifacts

### 6.4 Research / Knowledge Sidecar

Allowed steward input:

- approved report-only artifacts
- future alert entries whose `owner_plane` is `research_plane`

Rules:

- these may be summarized as non-blocking context
- they must not override `system_health_latest.json` or `daily_report_latest.json`
- they must not become a hidden dependency for P0 operator-facing status

## 7. Recovery / Notification Logic

Recommended read-only behavior:

1. load the newest approved artifact set
2. ignore entries whose `dedupe_key` is already suppressed inside the current cooldown window
3. if an entry sets `recovery_of`, emit a recovery notice only when the referenced alert was previously operator-visible
4. batch related alerts by `cooldown_key` for one Telegram summary
5. always cite `ssot_paths` or `evidence_paths` rather than inventing unstated context

Recommended message classes:

- proactive alert
- recovery notice
- scheduled summary line item

Forbidden message classes:

- speculative system recomputation
- ad-hoc repair proposal that bypasses documented `repair_class`
- free-form operator command suggestion that implies arbitrary exec

## 8. Degrade / Kill Switch / Incremental Adoption

Degrade:

- if a supplemental alert artifact is missing, keep `/status` and `/daily` on existing canonical SSOT behavior
- if both canonical SSOT and supplemental alert artifacts are missing, report `UNKNOWN` plus the existing `refresh_hint`
- missing sidecar alerts must not block top-level Telegram reporting

Kill switch:

- current prototype kill switch is `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0` and that remains the default
- the prototype must stay reversible without affecting the state writer, `/status`, or `/daily`

## 9. Prototype Shadow Path

Current prototype scope in `_local/telegram_cp/tg_cp_server.py`:

- disabled by default via `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`
- reads `reports/state_atomic/alerts_latest.json` first
- reads `reports/state_atomic/alerts_journal.jsonl` only as a fallback input when `alerts_latest.json` is absent
- emits runtime-log shadow summaries only
- prefixes shadow summaries with `INTERNAL_ONLY | SHADOW_ONLY | NOT_CANONICAL | NO_ACTIONING`
- does not send formal Telegram alerts
- does not rewrite `data/state/*`
- does not recompute `system_health_latest.json`
- does not alter `/status` or `/daily`

Prototype-only delivery behavior:

- `dedupe_key`: process-local duplicate suppression only
- `cooldown_key`: process-local cooldown only
- `recovery_of`: recovery shadow summary only when the referenced alert was previously surfaced by the same in-process prototype cache
- missing or unreadable artifact: graceful skip, no P0 impact

Prototype caveat:

- cache state is process-local and non-authoritative
- restart may clear suppression memory and cause repeated shadow summaries if the feature is manually enabled
- this is acceptable for prototype/shadow mode because no formal operator-visible Telegram notification is sent

Disposition note:

- current recommended posture is to keep shadow summary `internal-log only`; see `docs/architecture/shadow_summary_disposition_v1.md`
- lifecycle criteria for keep / upgrade / retire now live in `docs/architecture/prototype_retirement_criteria_v1.md`
- evidence collection for future upgrade / retire review now lives in `docs/architecture/prototype_evidence_collection_plan_v1.md`

Suggested follow-on adoption path:

1. producer-side artifact schema validation outside runtime
2. one small producer PR for atomic `alerts_latest.json` / `alerts_journal.jsonl`
   Current producer posture: manual-only helper, no schedule, no steward runtime dependency; see `docs/architecture/atomic_alert_producer_invocation_decision_v1.md`.
3. disabled-by-default shadow prototype may read artifacts only and emit no-op internal summaries only
4. only after shadow validation should a later PR revisit whether operator-visible Telegram summary is warranted; current disposition says no rollout yet
5. only after that, evaluate whether a canonical mirror under `data/state/*` is needed, and if so, route it only through `scripts/state_snapshots.py`
