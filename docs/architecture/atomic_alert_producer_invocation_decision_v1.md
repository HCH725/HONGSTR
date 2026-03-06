# HONGSTR Atomic Alert Producer Invocation Decision v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / ops-decision-first / no runtime wiring
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: producer invocation / schedule decision PR
Plane: non-core atomic producer invocation policy
Expected SSOT/output impact: none

## 0. Purpose

This file decides the current role and invocation posture for:

- `scripts/state_atomic/emit_atomic_alert_artifacts.py`
- `reports/state_atomic/alerts_latest.json`
- `reports/state_atomic/alerts_journal.jsonl`

The scope is intentionally narrow:

- classify the helper
- decide whether it should enter a schedule
- define kill switch and removal plan
- avoid touching `refresh_state`, `state_snapshots`, `tg_cp`, or any canonical `data/state/*` writer path

## 1. Decision Summary

Current decision:

- `emit_atomic_alert_artifacts.py` is `manual-only helper` in v1
- it is also `sample/dev-capable` because it can emit stable sample artifacts for schema validation
- it is **not** a scheduled producer in v1
- it is **not** a launchd-managed job in v1
- it is **not** a `refresh_state` step in v1

Direct answers:

- Should it enter a schedule now: `No`
- If a later PR needs controlled invocation, which comes first: `manual one-shot wrapper`, not launchd
- Why not schedule now: no live consumer exists yet, artifacts are non-canonical, the helper can fall back to sample output, and scheduling it now would create sidecar noise without improving Stage 2 SSOT behavior

## 2. Audited Scope

Paths reviewed for this decision:

- `scripts/state_atomic/emit_atomic_alert_artifacts.py`
- `reports/state_atomic/alerts_latest.json`
- `reports/state_atomic/alerts_journal.jsonl`
- `scripts/watchdog_status_snapshot.py`
- `scripts/refresh_state.sh`
- `scripts/state_snapshots.py`
- `scripts/check_state_writer_boundary.py`
- `docs/architecture/alert_artifact_skeleton_v1.md`
- `docs/architecture/central_steward_readonly_ingest_v1.md`
- `ops/launchagents/README.md`
- `docs/ops_obsidian_mirror.md`
- `.gitignore`

## 3. Current State

### 3.1 Producer graph

- `scripts/watchdog_status_snapshot.py` writes atomic watchdog output to `reports/state_atomic/watchdog_status_latest.json`
- `scripts/refresh_state.sh` calls `scripts/watchdog_status_snapshot.py` as an atomic pre-step
- `scripts/state_snapshots.py` remains the only writer allowed to publish canonical mirrors under `data/state/*`, including:
  - `data/state/watchdog_status_latest.json`
  - `data/state/services_heartbeat.json`
- `scripts/state_atomic/emit_atomic_alert_artifacts.py` writes only to:
  - `reports/state_atomic/alerts_latest.json`
  - `reports/state_atomic/alerts_journal.jsonl`

### 3.2 Tracking and runtime posture

- `reports/` is git-ignored, so generated `alerts_*` artifacts are runtime-only and non-canonical by default
- there is no existing launchd plist, install script, or workflow that invokes `emit_atomic_alert_artifacts.py`
- the helper is currently referenced only by itself and the alert/steward schema docs

### 3.3 Helper behavior that matters for scheduling

Current helper behavior:

- if watchdog atomic input exists, it derives a narrow control-plane alert from `reports/state_atomic/watchdog_status_latest.json`
- if watchdog input is missing or unreadable, it emits a stable sample fallback
- it does not write `data/state/*`
- it does not notify Telegram
- it does not wire into central steward

Scheduling implication:

- a scheduled run could emit sample fallback artifacts even when no real downstream consumer exists
- that would create churn in `reports/state_atomic/*` without improving canonical state or operator-facing output

## 4. Disposition

| Item | Current classification | Reason | Evidence | Next action |
|---|---|---|---|---|
| `scripts/state_atomic/emit_atomic_alert_artifacts.py` | `Manual-only helper` | non-core producer, not consumed by P0, and currently doubles as schema/sample generator | helper docstring and CLI defaults write only under `reports/state_atomic/*`; no runtime invoker found | keep manual-only |
| `scripts/state_atomic/emit_atomic_alert_artifacts.py --sample-only` | `Sample/dev-only mode` | safe for schema validation and docs/examples; not a production signal source | helper supports `--sample-only`; sample output verified under `/tmp/hongstr_atomic_alert_decision_verify` | keep for validation only |
| `reports/state_atomic/alerts_latest.json` | `Atomic artifact only` | intended future read-only ingest input, not canonical SSOT | schema docs define it as non-canonical; path is under ignored `reports/` | do not wire into `/status` or `/daily` |
| `reports/state_atomic/alerts_journal.jsonl` | `Atomic artifact only` | intended future journal for dedupe/cooldown history, not canonical SSOT | schema docs define it as non-canonical; path is under ignored `reports/` | do not wire into steward runtime yet |
| launchd schedule for alert producer | `Do not add now` | no existing consumer, no dedicated plane owner, and launchd would overstate runtime importance | `ops/launchagents/README.md` has no alert producer label; no plist exists | leave absent |
| `refresh_state` integration | `Forbidden in this step` | would blur the single-writer boundary and expand scope into Stage 2 runtime | `scripts/refresh_state.sh` is protected and out of scope for this PR | defer to separate approved PR only if ever needed |

## 5. Why It Should Not Enter A Schedule Yet

### 5.1 Stage 2 boundary

Stage 2 requires:

- atomic producers may run before canonical publication
- `scripts/state_snapshots.py` remains the only canonical `data/state/*` writer

This helper does not violate the writer boundary today because it stays under `reports/state_atomic/*`.

But scheduling it now would still be premature because:

- there is no approved consumer path from `alerts_*` into canonical publication
- there is no approved `refresh_state` handoff contract for these artifacts
- there is no evidence that scheduled alert artifacts improve deterministic fallback behavior

### 5.2 Stage 7 boundary

Stage 7 requires Telegram single-entry behavior and read-only reporting.

This helper is not a Stage 7 path today because:

- it does not invoke Telegram
- it does not call `_local/telegram_cp/**`
- it does not feed central steward runtime yet

That is precisely why it should stay manual-only for now:

- scheduling it before steward ingest exists would encourage a future reader to treat `alerts_*` as quasi-live state
- the current safe posture is to keep generation explicit, optional, and operator-controlled

### 5.3 Stage 8 boundary

Stage 8 sidecar/reporting capabilities must remain pausable and non-blocking.

This helper fits that posture only when it is:

- optional
- stoppable
- outside P0
- not launchd-owned

Manual-only invocation satisfies those constraints. A recurring schedule does not add enough value yet to justify the extra operational surface.

## 6. Recommended Invocation

Current recommendation:

- keep `emit_atomic_alert_artifacts.py` as a manual one-shot helper only

Recommended commands:

```bash
python3 scripts/state_atomic/emit_atomic_alert_artifacts.py --sample-only
python3 scripts/state_atomic/emit_atomic_alert_artifacts.py
```

Rules:

- output must stay under `reports/state_atomic/*`
- no invocation may write `data/state/*`
- no invocation may notify Telegram directly
- no invocation may be treated as P0-required for `/status` or `/daily`

### 6.1 If a later PR wants an invocation wrapper

The first acceptable step is:

- a docs-reviewed manual one-shot ops wrapper

The first unacceptable step is:

- adding a launchd plist immediately
- inserting the helper into `scripts/refresh_state.sh`
- teaching central steward to depend on these artifacts before read-only ingest is separately approved

Reason:

- launchd is reserved in this repo for durable plane owners or established scheduled jobs
- this helper has not yet crossed the threshold from validation helper to justified scheduled producer

## 7. Launchd / Wrapper Decision

Current answer:

- `manual-only`: yes
- `scheduled producer`: no
- `sample/dev-only`: partially yes, because the helper still contains a stable schema-validation mode
- `one-shot ops wrapper`: possible future follow-on, but docs-only for now
- `launchd`: no, not at this stage

If a future consumer exists, the order should be:

1. keep helper logic narrow
2. add a manual one-shot invocation wrapper only if operators need a cleaner entrypoint
3. validate that no consumer treats `alerts_*` as canonical truth
4. only then evaluate whether a schedule is justified

## 8. Degrade / Kill Switch / Removal Plan

Degrade:

- if the helper is never run, nothing breaks
- Stage 2 SSOT publication remains unchanged
- `/status` and `/daily` remain on canonical `data/state/*`
- missing `alerts_*` artifacts must degrade to “feature absent” rather than “state unknown”

Kill switch:

- do not schedule it
- stop invoking it manually if noise appears
- revert this docs PR or a future wrapper/schedule PR if the helper’s role changes

Removal plan:

1. keep the helper only while it is the smallest useful way to validate `alerts_*` schema
2. if a future steward ingest PR adopts a different producer contract, archive or remove this helper in a dedicated minimal PR
3. if no approved consumer emerges, retire the helper instead of promoting it into background runtime by inertia

## 9. Out Of Scope

This PR does not:

- modify `src/hongstr/**`
- modify `_local/telegram_cp/**`
- modify `scripts/refresh_state.sh`
- modify `scripts/state_snapshots.py`
- add a launchd plist
- add a workflow schedule
- wire `alerts_latest.json` or `alerts_journal.jsonl` into `/status`, `/daily`, or central steward runtime

## 10. Evidence Notes

Evidence used for this decision:

- `gh pr view 221` through `gh pr view 229`: stacked PR chain remains open, so this decision must stay a small stacked docs PR on top of `#229`
- `git ls-files reports/state_atomic`: no tracked `alerts_*` artifact in git
- `.gitignore`: `reports/` is ignored, so generated artifacts remain runtime-only
- `python3 scripts/state_atomic/emit_atomic_alert_artifacts.py --output-root /tmp/hongstr_atomic_alert_decision_verify --sample-only`: sample generation works without touching repo-tracked outputs
- `ops/launchagents/README.md`: no existing `com.hongstr.*` alert artifact producer owner
- `scripts/refresh_state.sh`: current atomic producer path includes watchdog snapshot but not alert artifact emission

## 11. Canonical Answer

The canonical invocation decision in v1 is:

- keep `scripts/state_atomic/emit_atomic_alert_artifacts.py` as a manual-only, stoppable, non-core helper
- do not put it into launchd
- do not insert it into `refresh_state`
- do not treat `alerts_*` as canonical state
- if a later PR needs cleaner invocation, start with a manual one-shot wrapper and re-review before any schedule is proposed
