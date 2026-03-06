# HONGSTR Escalation Taxonomy v1

Last updated: 2026-03-06 (UTC+8)  
Status: docs-only / policy-first / no runtime wiring  
Stage: Stage 2 / Stage 7 / Stage 8  
Checklist item: Escalation Taxonomy v1  
Plane: Cross-plane escalation and repair governance  
Expected SSOT/output impact: none

## 0. Purpose

This taxonomy answers four questions for every governance event:

- should the event be recorded only, or should it escalate
- if it escalates, who is the target
- whether coding-specialist bounded repair is permitted
- how cooldown and dedupe prevent repeated spam or duplicate repair attempts

The taxonomy is intentionally narrower than current repo capabilities. Where current tools are broader than policy, policy wins.

## 1. Stage Alignment

| Stage | Required invariant | Taxonomy consequence |
|---|---|---|
| Stage 2 | `scripts/state_snapshots.py` remains the only canonical writer; `/status`, `/daily`, and `/dashboard` stay deterministic and SSOT-only | any SSOT breach or dual-truth attempt escalates to Telegram or forbidden stop |
| Stage 7 | Telegram remains the single outward operator entrance; control plane is read-only | no specialist may message outward directly; no Telegram-driven free-form execution path |
| Stage 8 | research and knowledge layer stay report-only, allowlisted, and suppressible | research and sidecar events are record-only unless they threaten deterministic reporting or violate sidecar boundaries |

## 2. Severity Levels

| Severity | Meaning | Default target | Telegram proactive alert |
|---|---|---|---|
| `INFO` | normal lifecycle or dedupe/cooldown bookkeeping | `none` | no |
| `WARN` | degraded but non-blocking condition; SSOT truth still intact | `none` or `telegram_central_steward` | only if repeated or operator-visible |
| `ERROR` | user-visible break in SSOT refresh, `/daily`, `/status`, or bounded governance path | `telegram_central_steward` or `human_operator` | yes |
| `CRITICAL` | forbidden boundary breach or attempted unsafe execution / dual truth | `forbidden_stop` | yes, immediately |

## 3. Escalation Targets

| `escalation_target` | Use when | Allowed output |
|---|---|---|
| `none` | local record, summary inclusion, or dedupe bookkeeping only | no outward action |
| `telegram_central_steward` | operator must be informed through the single Telegram entrance | steward-formatted Telegram alert only |
| `coding_specialist` | a safe, allowlisted, reviewable repair can be prepared as a draft PR | draft PR, checks, evidence artifact |
| `repo_reviewer` | policy/doc merge decision is needed, but no runtime repair is allowed | issue, PR review, architecture comment |
| `human_operator` | manual intervention is required to inspect system state or scheduling | operator runbook action |
| `forbidden_stop` | any unsafe execution, core-path touch, or dual-truth attempt | reject, stop, and require human review |

## 4. Repair Classes

| `repair_class` | Meaning | Eligible paths |
|---|---|---|
| `record_only` | record the event, roll up later, no direct alert or repair | any non-authoritative report artifact |
| `telegram_notify` | alert through steward only; no automatic code change | SSOT failures, top-level consumer degradation |
| `bounded_repair` | coding specialist may prepare a minimal draft PR after allowlist checks | `docs/**`, `scripts/guardrail_check.sh`, `scripts/check_state_writer_boundary.py`, `scripts/self_heal/**`, `tests/test_self_heal_allowed_paths.py`, and future explicitly allowlisted governance-only paths |
| `manual_review` | architecture or operator decision required before any change | cross-plane or ambiguous ownership paths |
| `forbidden` | no repair delegation is allowed | `src/hongstr/**`, canonical writer boundary, unsafe execution surfaces, dual-truth paths |

## 5. Event Routing Matrix

| Event pattern | Severity | Escalation | Repair class | Policy |
|---|---|---|---|---|
| `research_report_ready`, `repair_dedupe_skip`, `repair_cooldown_skip`, `obsidian_export_done`, `lancedb_index_done` | `INFO` | `none` | `record_only` | log only; include in summary if useful |
| `research_warn_nonblocking`, `obsidian_export_warn`, `lancedb_index_warn`, `deterministic_fallback_used` | `WARN` | `none` by default | `record_only` | do not wake operator unless repetition crosses cooldown threshold |
| `ssot_refresh_failed`, `ssot_input_missing`, `ssot_input_unreadable`, `daily_report_missing`, `daily_report_unreadable`, `system_health_fail` | `ERROR` | `telegram_central_steward` | `telegram_notify` | proactive Telegram alert is required |
| `repair_candidate_detected` with evidence limited to allowlisted docs/guardrail paths | `WARN` | `coding_specialist` | `bounded_repair` | specialist may prepare a smallest-unit draft PR |
| `repair_blocked_allowlist`, `repair_blocked_policy` | `WARN` or `ERROR` | `repo_reviewer` | `manual_review` | stop autonomous repair and ask for scope clarification in PR/issue |
| `forbidden_path_touch`, `second_state_writer_attempt`, `sidecar_truth_source_attempt`, `unsafe_exec_path_attempt`, `artifact_commit_attempt`, `secret_exposure_attempt` | `CRITICAL` | `forbidden_stop` | `forbidden` | immediate stop; no delegated repair |

## 6. Telegram Proactive Alert Rules

Telegram alerts are required only when at least one of the following is true:

- canonical SSOT inputs for `/status` or `/daily` are missing or unreadable
- `scripts/refresh_state.sh` cannot produce a deterministic top-level output
- a forbidden boundary is crossed or attempted
- user-visible `UNKNOWN` / degraded status will persist until operator action

Telegram alerts are not required for:

- research or knowledge sidecar success events
- dedupe/cooldown bookkeeping
- report-only artifacts that do not affect top-level state
- allowlisted docs-first repair candidates that have no operator-facing impact yet

Only the central steward may send the final Telegram message. Coding and quant specialists must emit evidence only.

## 7. Bounded Repair Policy

Coding-specialist bounded repair is permitted only when all conditions hold:

- the event evidence points to a reviewable, non-core governance path
- the smallest PR can stay isolated from open governance PRs by stacking, not by expanding the old diff
- the repair does not modify `src/hongstr/**`
- the repair does not modify `scripts/state_snapshots.py`, `scripts/refresh_state.sh`, or `_local/telegram_cp/tg_cp_server.py`
- the repair does not create a second writer, alternate truth source, or direct execution path
- the repair ends as a draft PR, not as an auto-merged runtime mutation

Examples that qualify in principle:

- docs/schema drift under `docs/architecture/**`
- policy drift between `docs/guardrails_dedupe.md` and later normative governance docs
- allowlist or check drift under `scripts/check_state_writer_boundary.py`, `scripts/guardrail_check.sh`, `scripts/self_heal/**`

Examples that do not qualify:

- any change under `src/hongstr/**`
- any change that makes Telegram dispatch commands directly to a coding agent
- any change that lets Obsidian or LanceDB feed `/status` or `/daily`
- any change that writes canonical `data/state/*` outside the state plane

## 8. Forbidden Classes

These are always `forbidden`, even if someone proposes a small diff:

- touching `src/hongstr/**`
- creating or endorsing a second `data/state/*` writer
- making `_local/telegram_cp/tg_cp_server.py` an arbitrary executor
- routing top-level status through `_local/obsidian_vault/**`, `_local/lancedb/**`, or mirror output
- committing `data/**`, `.parquet`, `.pkl`, LanceDB local data, or mirror artifacts
- bypassing Telegram as the outward operator entrance

## 9. Cooldown and Dedupe Rules

### 9.1 `dedupe_key`

`dedupe_key` answers: "is this the same event meaningfully repeated?"

Recommended normalization:

- same `event_type`
- same impacted component or path set
- same repair class
- same normalized summary hash

If those are unchanged, repeated events should not create new repair attempts.

### 9.2 `cooldown_key`

`cooldown_key` answers: "even if this is not a literal duplicate, should alerts be suppressed for a while?"

Recommended grouping:

- `<event_type>:<component>:<escalation_target>`
- `<repair_class>:<path_scope>`

Recommended minimum windows:

| Class | Suggested cooldown |
|---|---|
| `record_only` info events | 15 minutes |
| sidecar warns | 30 minutes |
| Telegram alerts for SSOT degradation | 60 minutes |
| bounded repair proposals for same path scope | 24 hours |
| forbidden events | no initial suppression; after first alert, aggregate repeat notices hourly |

## 10. Degrade / Kill Switch / Removal Plan

Current degrade stance:

- if taxonomy wiring does not exist yet, keep recording decisions in docs and PR bodies only
- when unsure, downgrade autonomy and upgrade human review

Current kill switch:

- do not wire this taxonomy into runtime until a later allowlisted PR
- if a future integration becomes noisy or risky, disable the integration point and fall back to manual review

Removal plan for mis-scoped automation:

1. disable the offending dispatcher, poller, or notification hook
2. preserve evidence artifacts for review
3. revert the integration PR
4. keep Stage 2 and Stage 7 baseline behavior only
