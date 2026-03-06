# HONGSTR Prototype Retirement Criteria v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / criteria-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype retirement criteria PR
Plane: central steward prototype lifecycle governance
Expected SSOT/output impact: none

## 0. Purpose

This file defines the lifecycle criteria for the current central steward shadow/prototype ingest path.

The only lifecycle question is:

1. when to keep it
2. when to consider upgrading it
3. when to retire or archive it

This file does not change runtime behavior.

Supporting evidence collection plan now lives in `docs/architecture/prototype_evidence_collection_plan_v1.md`.
Reusable review templates now live in `docs/templates/prototype_upgrade_review_template_v1.md` and `docs/templates/prototype_retirement_review_template_v1.md`.
Review kickoff procedure now lives in `docs/ops/prototype_review_kickoff_sop_v1.md`.

## 1. Current State Summary

Current prototype scope:

- producer-side artifacts remain:
  - `reports/state_atomic/alerts_latest.json`
  - `reports/state_atomic/alerts_journal.jsonl`
- current steward prototype remains:
  - default-off via `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`
  - internal-log only
  - read-only against atomic artifacts
  - process-local for `dedupe_key`, `cooldown_key`, and `recovery_of`
  - explicitly labeled `INTERNAL_ONLY | SHADOW_ONLY | NOT_CANONICAL | NO_ACTIONING`

Current prototype does:

- read `alerts_latest.json` first
- fall back to `alerts_journal.jsonl` only when `alerts_latest.json` is absent
- suppress duplicates within process scope
- apply process-local cooldown
- emit recovery shadow summary only when a predecessor alert was already surfaced in the same process-local cache
- write shadow output only to internal runtime log

Current prototype does not:

- send formal Telegram alerts
- alter `/status`
- alter `/daily`
- alter `/dashboard`
- write `data/state/*`
- recompute canonical system state
- invoke bounded repair or arbitrary exec

## 2. Canonical Boundary

### 2.1 Stage 2

Stage 2 boundary remains:

- `scripts/state_snapshots.py` is the only canonical writer for `data/state/*`
- `refresh_state.sh` and the state-plane writer remain the canonical publication path
- missing supplemental artifacts must degrade without affecting deterministic SSOT fallback

Criteria implication:

- the prototype must never become a second writer
- the prototype must never publish canonical state
- the prototype must never become required for `/status`, `/daily`, or dashboard truth

### 2.2 Stage 7

Stage 7 boundary remains:

- Telegram is the single operator entry surface
- reporting is read-only
- command surface remains minimal

Criteria implication:

- any operator-visible evolution must not blur the line between:
  - formal alert
  - non-canonical prototype summary

### 2.3 Stage 8

Stage 8 boundary remains:

- prototype / report-only / pausable / allowlisted

Criteria implication:

- the prototype is acceptable only while it remains pausable, non-blocking, and outside the P0 path

## 3. Keep Criteria

The prototype may remain in `Keep` status only when all of the following are true:

| Criterion | Required evidence | Next action if true | Kill switch if false |
|---|---|---|---|
| default-off posture remains intact | `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0` stays the documented default | keep as observation-only path | revert to docs-only if anyone proposes always-on behavior |
| internal-only posture remains intact | runtime output stays in process-local log only; no Telegram-visible message path | keep observing dedupe/cooldown/recovery behavior | do not approve any message-surface change in the same PR |
| no canonical dependency exists | `/status`, `/daily`, and dashboard still read canonical `data/state/*` only | keep prototype out of P0 | stop if any future change tries to consume shadow output as truth |
| atomic artifacts remain non-canonical | `alerts_*` stay under `reports/state_atomic/*` and are not mirrored into `data/state/*` | keep producer/steward split clean | reject any attempt to publish them as top-level SSOT |
| prototype remains stoppable | disabling the flag produces clean no-op behavior | keep as pausable Stage 8 side path | disable or remove if stoppability is lost |

Keep rationale:

- this path is still useful as a low-risk staging layer between docs-only design and any future human-visible experiment
- it stays acceptable only while it remains obviously non-canonical and non-actioning

## 4. Upgrade Criteria

The prototype may be considered for `Upgrade` only when every upgrade criterion below is satisfied with concrete evidence.

Upgrade here means only:

- a later PR may *consider* operator-visible but explicitly non-canonical Telegram shadow summary

Upgrade does not mean:

- canonical state
- formal alerting
- bounded repair
- `/status` or `/daily` dependency

| Criterion | Evidence threshold | Next action if met | Kill switch if not met |
|---|---|---|---|
| producer contract stability | alert artifact schema is stable enough that sample/dev fallback is no longer the main validation mode | open a dedicated runtime PR for message-surface review only | remain internal-log only |
| message distinction is testable | proposed visible text is unmistakably labeled `SHADOW SUMMARY`, `NOT CANONICAL`, `NOT A FORMAL ALERT`, and `NO ACTION REQUIRED UNLESS CONFIRMED BY /status OR /daily` | review wording in docs before runtime wiring | reject operator-visible rollout |
| operational usefulness is evidenced | internal review shows shadow summary meaningfully improves operator comprehension beyond internal logs | justify a tiny operator-visible experiment | stay in observation mode |
| confusion risk is bounded | docs and operator guidance explicitly separate formal alerts from shadow summary | gate rollout behind separate feature flag and explicit labeling | do not collapse visible classes |
| no P0 dependency emerges | missing shadow artifacts still have zero impact on canonical reporting | keep rollout optional and reversible | do not approve visible rollout |
| single-entry semantics survive | Telegram remains the only visible surface, and shadow summary does not bypass current alert governance | proceed only as explicitly non-canonical side message | stop if it introduces a parallel truth path |

Upgrade rationale:

- upgrade must be evidence-based, not preference-based
- “this feels useful” is insufficient
- operator-visible shadow summary requires proof that the message class can remain clearly secondary to formal alerts and canonical SSOT

## 5. Retirement Criteria

The prototype should enter `Retirement candidate` status when one or more of the following becomes true:

| Criterion | Evidence | Next action | Kill switch / removal plan |
|---|---|---|---|
| observation value remains low | repeated internal observation yields no meaningful operator or governance insight | open dedicated retirement PR | remove runtime path and leave docs/history note |
| producer contract diverges | a better producer/steward design supersedes this path | archive this prototype rather than adapting it indefinitely | retire the prototype in a separate minimal PR |
| confusion risk starts rising | surrounding proposals keep trying to make it quasi-alerting without meeting upgrade criteria | move to retirement instead of ambiguous expansion | reject rollout and archive if pressure persists |
| maintenance cost exceeds value | the prototype requires recurring clarification or defensive wording without producing commensurate evidence | stop carrying it forward | archive docs and remove runtime hook later |
| boundary erosion appears | any future change tries to make it canonical, actioning, or required for top-level truth | treat as governance failure signal | disable and remove rather than weaken the SSOT boundary |

Retirement rationale:

- the prototype should not persist forever by inertia
- if it stays low-value or repeatedly tempts boundary erosion, archive is cleaner than indefinite ambiguity

## 6. Current Recommended Status

Recommended current status:

- `Keep`
- qualifier: `upgrade-observation only`

Plain meaning:

- keep the prototype for now
- do not upgrade it yet
- do not treat it as a retirement candidate yet
- continue using it only as an internal observation layer until stronger evidence exists

Why this is the current recommendation:

- the path remains safely bounded today
- the path is still too immature for operator-visible rollout
- the path still has enough staging value that immediate retirement would be premature

## 7. Degrade / Kill Switch / Removal Plan

Degrade:

- if the feature flag stays off, nothing changes
- if artifacts are missing, the prototype continues to skip cleanly
- `/status`, `/daily`, and dashboard truth remain unchanged

Kill switch:

- keep `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0` as the default
- if manually enabled for local observation, turn it back off immediately to return to noop behavior
- if future proposals skip the upgrade criteria, reject rollout and keep internal-only mode

Removal plan:

1. keep the prototype only while it remains clearly non-canonical, non-actioning, and low-cost
2. if retirement criteria are met, open a dedicated minimal PR to remove the runtime hook and archive the docs note
3. do not mix retirement with unrelated alerting or state-plane changes

## 8. Canonical Answer

The canonical lifecycle answer in v1 is:

- current status is `Keep`
- operational posture is `upgrade-observation only`
- upgrade is blocked until evidence-based criteria are met
- retirement should be preferred over boundary erosion if the prototype stops earning its place
