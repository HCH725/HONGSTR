# HONGSTR Shadow Summary Disposition v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / decision-first / no rollout
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: shadow summary disposition PR
Plane: central steward prototype disposition
Expected SSOT/output impact: none

## 0. Purpose

This file decides the next-step posture for the central steward shadow summary path introduced in the disabled-by-default prototype.

The only decision question is:

1. keep shadow summary `internal-log only`
2. upgrade it to `operator-visible but explicitly non-canonical Telegram shadow summary`
3. `retire / archive` the prototype path

This file does not roll out any runtime change.

Supporting evidence collection plan now lives in `docs/architecture/prototype_evidence_collection_plan_v1.md`.

## 1. Current State

Current prototype behavior in `_local/telegram_cp/tg_cp_server.py`:

- gated by `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0` by default
- reads `reports/state_atomic/alerts_latest.json` first
- falls back to `reports/state_atomic/alerts_journal.jsonl` only when `alerts_latest.json` is absent
- applies process-local `dedupe_key` suppression
- applies process-local `cooldown_key` suppression
- emits recovery shadow summary only when `recovery_of` refers to a previously surfaced alert inside the same in-process cache
- writes shadow output only through `runtime.log`
- prefixes each runtime-log summary with `INTERNAL_ONLY | SHADOW_ONLY | NOT_CANONICAL | NO_ACTIONING`
- does not call `_send(...)`
- does not rewrite `data/state/*`
- does not alter `/status`
- does not alter `/daily`

Current artifact role:

- `reports/state_atomic/alerts_latest.json` is non-canonical latest alert input only
- `reports/state_atomic/alerts_journal.jsonl` is non-canonical alert history input only
- both stay under `reports/state_atomic/*`, not `data/state/*`

Current canonical truth boundary:

- `/status` stays on canonical SSOT, centered on `data/state/system_health_latest.json` and other approved `data/state/*` sources
- `/daily` stays on canonical `data/state/daily_report_latest.json`
- dashboard truth remains on existing canonical `data/state/*` files
- no alert artifact may replace or recompute those top-level surfaces

Current formal alerting boundary:

- the repo already has a separate scheduled alert path through `alerts_pending.jsonl` and `_poll_and_forward_alerts()`
- that path is materially different from the shadow prototype because it is operator-visible

## 2. Why This Decision Matters

The shadow prototype is intentionally harmless today because it is:

- default-off
- internal-only
- non-canonical
- delivery-local
- explicitly marked as `NO_ACTIONING`

The moment it becomes operator-visible in Telegram, it crosses a different review bar:

- it can be mistaken for a formal alert
- it shares the same steward entry surface as operator-visible messages
- it can create expectation that the message reflects canonical system truth

That is the main governance risk this decision must resolve.

## 3. Stage Alignment

### 3.1 Stage 2

Stage 2 requires:

- single canonical writer for `data/state/*`
- deterministic fallback
- `refresh_state` and `state_snapshots` remain the canonical publication path

Disposition rule:

- shadow summary must never become canonical state
- shadow summary must never be written into `data/state/*`
- shadow summary must never cause `tg_cp` to recompute `system_health_latest.json` or `daily_report_latest.json`

### 3.2 Stage 7

Stage 7 requires:

- Telegram remains the single operator entry surface
- reporting stays read-only
- command surface stays minimal

Disposition rule:

- operator-visible shadow summary is only thinkable if it is explicitly labeled non-canonical and non-actioning
- even then, it must not be confused with formal alerting or `/status` `/daily`

### 3.3 Stage 8

Stage 8 allows:

- prototype
- report-only
- allowlisted side channels
- pausable capability

Disposition rule:

- internal-log-only shadow summary fits Stage 8 cleanly today
- operator-visible shadow summary could fit Stage 8 only as an explicitly marked prototype side channel, not as production alerting

## 4. Option Comparison

## 4.1 Option 1: Keep `internal-log only`

What it means:

- keep `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0` as default
- if manually enabled, keep output in process-local `runtime.log` only
- do not send operator-visible Telegram shadow messages

Pros:

- lowest confusion risk
- preserves clean separation from formal alerting
- preserves Stage 2 SSOT boundary without ambiguity
- keeps Stage 7 Telegram semantics simple
- keeps Stage 8 prototype path pausable and non-blocking
- allows continued observation of ingest behavior before any operator-facing decision

Cons:

- low operator feedback value
- no human-visible proof that dedupe/cooldown/recovery text is useful
- slower path to validating message design

Risks:

- limited signal on whether the prototype is worth keeping long-term
- process-local cache behavior is only indirectly observable through logs

Kill switch:

- keep `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`
- if manually enabled, set it back to `0`

Next step if chosen:

- keep gathering low-risk evidence
- later decide either `operator-visible prototype` or `retire`

## 4.2 Option 2: Upgrade to `operator-visible but explicitly non-canonical Telegram shadow summary`

What it means:

- steward may send a Telegram message, but it must be clearly labeled as:
  - `SHADOW SUMMARY`
  - `NOT CANONICAL`
  - `NOT A FORMAL ALERT`
  - `NO ACTION REQUIRED UNLESS CONFIRMED BY /status OR /daily`

Pros:

- validates whether the summary is actually useful to an operator
- tests messaging format, dedupe wording, and recovery wording on the real channel
- still keeps Telegram as the single visible operator surface

Cons:

- materially raises confusion risk
- introduces two operator-visible classes in the same channel:
  - formal alert
  - non-formal shadow summary
- invites users to treat shadow output as quasi-alerting even if explicitly labeled otherwise

Risks:

- operator may mistake shadow summary for canonical truth
- operator may react to shadow summary before verifying `/status` or `/daily`
- process-local dedupe/cooldown cache could produce inconsistent visible behavior across restarts
- sidecar artifact quality could be over-trusted before producer/steward contracts are mature

Kill switch:

- separate feature flag would be mandatory
- visible prefixing would be mandatory
- revert to internal-log-only immediately if confusion appears

Next step if chosen:

- do a separate minimal runtime PR only
- require explicit text markers and no-formal-alert wording
- require additional docs covering operator interpretation rules

## 4.3 Option 3: `Retire / archive`

What it means:

- remove or archive the shadow summary prototype path
- keep atomic artifacts producer-side only
- abandon steward-side shadow observation for now

Pros:

- removes even the possibility of future shadow/final confusion
- reduces runtime surface
- simplifies central steward further

Cons:

- discards the lowest-risk place to evaluate dedupe/cooldown/recovery behavior
- makes the recent prototype work effectively one-step disposable
- removes a useful staging area between `no consumer` and `operator-visible consumer`

Risks:

- future steward ingest work may be forced to jump directly from docs to human-visible behavior
- less opportunity to validate producer/steward contract quality before exposure

Kill switch:

- dedicated runtime-removal PR later

Next step if chosen:

- archive docs and remove prototype code path
- keep future steward work docs-only until a stronger use case exists

## 5. Recommendation

Recommended option: `Option 1 — keep internal-log only`

Reason:

- it is the only option that fully preserves current Stage 2 / Stage 7 / Stage 8 guardrails without adding message-class ambiguity
- the current producer is still manual-only and non-canonical
- the current steward suppression cache is still process-local and therefore not strong enough for human-visible interpretation
- the repo already has a formal alert path, so adding a second visible class too early would create avoidable ambiguity
- the runtime path is now explicitly hardened to log `INTERNAL_ONLY | SHADOW_ONLY | NOT_CANONICAL | NO_ACTIONING`, which is enough for prototype observation without rollout
- retire/archive is premature because the prototype still provides a useful low-risk observation layer

Short version:

- `upgrade to visible`: too early
- `retire`: too early
- `internal-log only`: correct next step

## 6. If Option 2 Is Ever Revisited

These preconditions should be required before considering operator-visible shadow summary:

- producer contract is stable enough that sample/dev artifacts are no longer the main validation mode
- shadow wording is proven useful through internal review
- visible messages are prefixed with unmistakable non-canonical markers
- formal alert and shadow summary have clearly different labels and trigger conditions
- docs explicitly instruct operators to confirm with `/status` or `/daily` before acting

If those preconditions are not met, option 2 should not proceed.

## 7. Degrade / Kill Switch / Removal Plan

Degrade:

- with option 1, missing artifacts or disabled flag continue to result in silent skip only
- `/status`, `/daily`, and dashboard truth remain unchanged
- no P0 dependency is added

Kill switch:

- keep `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0` as default
- if manually enabled for local testing, set it back to `0`
- close or revert the later rollout PR if anyone proposes operator-visible shadow output before the boundary is mature

Removal plan:

1. keep shadow summary internal-only while evidence remains limited
2. if it provides no value after observation, retire it in a dedicated minimal PR
3. if value is proven, revisit option 2 in a separate runtime PR with explicit non-canonical labeling

## 8. Canonical Answer

The canonical disposition in v1 is:

- keep central steward shadow summary `internal-log only`
- do not upgrade it to operator-visible Telegram output yet
- do not retire it yet
- lifecycle criteria now live in `docs/architecture/prototype_retirement_criteria_v1.md`
- revisit operator-visible shadow summary only in a later dedicated runtime PR if clearer value and safer labeling are demonstrated
