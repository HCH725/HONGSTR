# HONGSTR Agent Event Schema v1

Last updated: 2026-03-06 (UTC+8)  
Status: docs-only / schema-first / no runtime wiring  
Stage: Stage 2 / Stage 7 / Stage 8  
Checklist item: Agent Event Schema v1  
Plane: State Plane + Control Plane + Research Plane governance contract  
Expected SSOT/output impact: none

## 0. Scope

This file defines the minimum event contract for agent-facing governance in HONGSTR.

This schema exists to support three constraints at the same time:

- Stage 2: keep `scripts/state_snapshots.py` as the only canonical `data/state/*` writer, with deterministic fallback through `bash scripts/refresh_state.sh`
- Stage 7: keep Telegram as the single outward operator entrance, with read-only top-level reporting
- Stage 8: keep knowledge and research outputs report-only, allowlisted, and suppressible via cooldown/dedupe

This file does not create a new runtime, storage path, queue, or writer. Future persistence is intentionally undefined in this PR so the schema cannot be mistaken for a second state writer.

## 1. Hard Red Lines

The following remain forbidden regardless of event content:

- any mutation under `src/hongstr/**`
- any second canonical writer for `data/state/*` outside `scripts/state_snapshots.py`
- any top-level `/status`, `/daily`, or `/dashboard` truth derived from Obsidian, LanceDB, or live external APIs
- any path that turns `_local/telegram_cp/tg_cp_server.py` into arbitrary command execution
- any direct specialist-to-Telegram outward messaging path that bypasses the central steward
- any repo-tracked `data/**`, `.parquet`, `.pkl`, LanceDB local artifacts, mirror outputs, or secrets

## 2. Canonical Producer / Consumer Model

The schema assumes this governance flow:

- State Plane produces deterministic SSOT files through `scripts/refresh_state.sh` -> `scripts/state_snapshots.py`
- specialists produce evidence artifacts, reports, or draft repairs only
- the central steward is the only component allowed to convert an event into an outward Telegram message
- missing or unreadable SSOT must degrade to `UNKNOWN` plus `refresh_hint`, never to live recomputation

## 3. Required Fields

Every v1 event must contain all fields below.

| Field | Type | Required | Rule |
|---|---|---|---|
| `event_id` | string | yes | Stable unique ID. Recommended format: `aev1_<ulid>` or UUIDv7. |
| `ts_utc` | string | yes | RFC 3339 / ISO 8601 UTC timestamp, for example `2026-03-06T09:40:00Z`. |
| `event_type` | string | yes | One of the event types in Section 4. |
| `agent_role` | string | yes | One of: `central_steward`, `coding_specialist`, `quant_specialist`, `state_plane`, `control_plane`, `research_plane`. |
| `severity` | string | yes | One of: `INFO`, `WARN`, `ERROR`, `CRITICAL`. |
| `summary` | string | yes | One-sentence human summary, max 240 chars, no hidden execution intent. |
| `evidence_paths` | array[string] | yes | Repo-relative evidence paths only. Empty array allowed when no durable evidence exists yet. |
| `next_action` | string | yes | One of the controlled actions in Section 5. |
| `escalation_required` | boolean | yes | `true` only when this event must be routed beyond local recording. |
| `escalation_target` | string | yes | One of the targets in Section 6. |
| `repair_class` | string | yes | One of: `record_only`, `telegram_notify`, `bounded_repair`, `manual_review`, `forbidden`. |
| `cooldown_key` | string | yes | Stable bucket for notification suppression, typically `<event_type>:<component>:<target>`. |
| `dedupe_key` | string | yes | Stable duplicate key for same event meaning, typically derived from event type + normalized scope + summary hash. |

## 4. Event Type Vocabulary v1

The minimum v1 vocabulary is grouped by governance purpose.

### 4.1 SSOT / deterministic health events

- `ssot_refresh_started`
- `ssot_refresh_succeeded`
- `ssot_refresh_failed`
- `ssot_input_missing`
- `ssot_input_unreadable`
- `system_health_warn`
- `system_health_fail`
- `daily_report_missing`
- `daily_report_unreadable`
- `deterministic_fallback_used`

### 4.2 Control-plane / Telegram safety events

- `telegram_command_refused`
- `telegram_read_only_report_sent`
- `telegram_exec_request_blocked`
- `steward_alert_sent`
- `steward_alert_suppressed_dedupe`

### 4.3 Coding-specialist repair governance events

- `repair_candidate_detected`
- `repair_pr_opened`
- `repair_blocked_allowlist`
- `repair_blocked_policy`
- `repair_cooldown_skip`
- `repair_dedupe_skip`

### 4.4 Research / knowledge sidecar events

- `research_report_ready`
- `research_warn_nonblocking`
- `obsidian_export_done`
- `obsidian_export_warn`
- `lancedb_index_done`
- `lancedb_index_warn`

### 4.5 Forbidden boundary events

- `forbidden_path_touch`
- `second_state_writer_attempt`
- `sidecar_truth_source_attempt`
- `unsafe_exec_path_attempt`
- `artifact_commit_attempt`
- `secret_exposure_attempt`

## 5. `next_action` Controlled Vocabulary

`next_action` must use a bounded value set, not open-ended prose. v1 allows:

- `none`
- `record_for_summary`
- `run_refresh_state`
- `inspect_ssot_inputs`
- `send_telegram_alert`
- `open_docs_pr`
- `open_guardrail_pr`
- `request_manual_review`
- `reject_and_stop`

Interpretation rules:

- `run_refresh_state` is the only allowed recovery hint for missing or stale top-level SSOT
- `open_docs_pr` and `open_guardrail_pr` are advisory only; they do not authorize runtime execution
- `reject_and_stop` is mandatory for forbidden events

## 6. `escalation_target` Vocabulary

v1 supports these targets:

- `none`
- `telegram_central_steward`
- `coding_specialist`
- `repo_reviewer`
- `human_operator`
- `forbidden_stop`

Routing rules:

- only `telegram_central_steward` may result in outward Telegram delivery
- `coding_specialist` may produce a bounded draft PR only when the repair class is `bounded_repair`
- `forbidden_stop` means stop routing and require human review before any code change

## 7. Routing Matrix

| Event family | Default severity | Record only | Telegram proactive alert | Coding specialist bounded repair | Forbidden |
|---|---|---|---|---|---|
| `research_report_ready`, `obsidian_export_done`, `lancedb_index_done`, `repair_dedupe_skip`, `repair_cooldown_skip` | `INFO` | yes | no | no | no |
| `obsidian_export_warn`, `lancedb_index_warn`, `research_warn_nonblocking`, `deterministic_fallback_used` | `WARN` | yes | only if repeated and user-visible | no | no |
| `ssot_input_missing`, `ssot_input_unreadable`, `daily_report_missing`, `daily_report_unreadable`, `system_health_fail`, `ssot_refresh_failed` | `ERROR` | no | yes | only after human review; no auto repair in v1 | no |
| `repair_candidate_detected`, `repair_pr_opened`, `repair_blocked_allowlist` | `WARN` | yes | optional summary only | yes, allowlist-only | no |
| `forbidden_path_touch`, `second_state_writer_attempt`, `sidecar_truth_source_attempt`, `unsafe_exec_path_attempt`, `artifact_commit_attempt`, `secret_exposure_attempt` | `CRITICAL` | no | yes | no | yes |

## 8. Bounded Repair Eligibility

An event may set `repair_class=bounded_repair` only when all conditions hold:

- proposed scope is limited to `docs/**`, `scripts/guardrail_check.sh`, `scripts/check_state_writer_boundary.py`, `scripts/self_heal/**`, `tests/test_self_heal_allowed_paths.py`, or other explicitly allowlisted non-core governance paths in a later PR
- no change is required under `src/hongstr/**`, `scripts/state_snapshots.py`, `scripts/refresh_state.sh`, `_local/telegram_cp/tg_cp_server.py`, `web/app/api/status/route.ts`, or any canonical SSOT consumer/producer runtime
- the output remains a draft PR or docs artifact, not direct execution
- evidence paths are concrete and reviewable

If any one of those conditions is false, the event must become `manual_review` or `forbidden`.

## 9. Forbidden Classification Rules

These combinations are always invalid:

- `repair_class=bounded_repair` with `event_type=second_state_writer_attempt`
- `escalation_target=coding_specialist` for any event whose fix requires changing `src/hongstr/**`
- `next_action=open_guardrail_pr` when the only evidence is a live API response
- `event_type=sidecar_truth_source_attempt` with `severity` below `CRITICAL`

Any event that would cause dual truth, unsafe execution, or non-deterministic top-level status must be normalized to:

- `repair_class=forbidden`
- `escalation_required=true`
- `escalation_target=forbidden_stop`
- `next_action=reject_and_stop`

## 10. JSON Example

```json
{
  "event_id": "aev1_01JW9J7AX6CKV9CMBT2W7M8B6V",
  "ts_utc": "2026-03-06T09:40:00Z",
  "event_type": "ssot_input_missing",
  "agent_role": "state_plane",
  "severity": "ERROR",
  "summary": "system_health_latest.json missing; top-level status must degrade to UNKNOWN.",
  "evidence_paths": [
    "scripts/refresh_state.sh",
    "scripts/state_snapshots.py",
    "docs/ops/telegram_operator_manual.md"
  ],
  "next_action": "run_refresh_state",
  "escalation_required": true,
  "escalation_target": "telegram_central_steward",
  "repair_class": "telegram_notify",
  "cooldown_key": "ssot_input_missing:system_health:telegram_central_steward",
  "dedupe_key": "ssot_input_missing:system_health_latest.json:missing"
}
```

## 11. Deterministic Degrade

If an emitter cannot load required evidence or SSOT input:

- keep the event structure valid
- lower confidence in `summary`, not in schema completeness
- set `next_action=run_refresh_state` or `request_manual_review`
- never substitute live recomputation for `/status` or `/daily`

## 12. Kill Switch / Rollback / Incremental Adoption

This PR is docs-only, so the current kill switch is trivial:

- do not wire the schema into runtime yet
- revert the docs commit or close the stacked PR if the vocabulary needs to change

Suggested follow-on adoption path:

1. add a non-canonical validator for event payload shape in docs/tests only
2. integrate schema output into report-only specialist artifacts
3. let the central steward consume the schema only after Stage 2 and Stage 7 checks stay green
