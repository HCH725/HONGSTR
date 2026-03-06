# HONGSTR Prototype Evidence Collection Plan v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-first / evidence-plan-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype evidence collection plan PR
Plane: central steward prototype evidence governance
Expected SSOT/output impact: none

## 0. Purpose

This file defines the evidence collection plan for the current central steward shadow/prototype ingest path.

The only question it answers is:

- if a later PR wants to judge `keep`, `upgrade`, or `retire`, what evidence must be collected first

This file does not change runtime behavior.

## 1. Current State Summary

Current prototype scope:

- producer-side artifacts remain:
  - `reports/state_atomic/alerts_latest.json`
  - `reports/state_atomic/alerts_journal.jsonl`
- current steward prototype remains:
  - default-off via `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0`
  - read-only against `reports/state_atomic/*`
  - internal-log only
  - process-local for `dedupe_key`, `cooldown_key`, and `recovery_of`
  - explicitly labeled `INTERNAL_ONLY | SHADOW_ONLY | NOT_CANONICAL | NO_ACTIONING`

Current prototype does:

- read `alerts_latest.json` first
- fall back to `alerts_journal.jsonl` only when `alerts_latest.json` is absent
- suppress duplicates within process scope
- apply process-local cooldown
- emit recovery shadow summary only when the predecessor alert was already visible to the same in-process cache
- write shadow output only to internal runtime log

Current prototype does not:

- send formal Telegram alerts
- alter `/status`
- alter `/daily`
- alter `/dashboard`
- write `data/state/*`
- become canonical SSOT
- trigger bounded repair or arbitrary exec

## 2. Why Evidence Collection Is Needed

Evidence collection is required because future lifecycle decisions must be based on observed value and observed risk, not on intuition.

The plan exists to answer these concrete questions:

- does the prototype produce useful shadow summaries often enough to justify its existence
- does `dedupe_key` suppression reduce visible noise in a meaningful way
- does `cooldown_key` suppression behave predictably enough to be trusted in a future review
- does `recovery_of` add useful context or mostly add churn
- does the prototype provide information that is not already obvious from canonical SSOT or formal alerting
- does the prototype create confusion pressure that would argue for retirement instead of upgrade

## 3. Evidence To Collect

All future reviews should collect the following evidence explicitly.

### 3.1 Shadow summary generation frequency

Question answered:

- how often does the prototype actually emit a summary when manually observed

Evidence to capture:

- observation session count
- number of candidate alert artifacts seen
- number of shadow summaries emitted
- number of sessions with zero emitted shadow summaries

Suggested interpretation:

- very low emission frequency may indicate the path has little practical value
- very high emission frequency may indicate noise pressure

### 3.2 Dedupe hit rate

Question answered:

- does `dedupe_key` materially suppress repeated noise

Evidence to capture:

- number of candidate entries read
- number of duplicate suppressions
- dedupe hit rate = duplicate suppressions / candidate entries read

Suggested interpretation:

- near-zero dedupe hit rate across the whole observation window suggests the feature adds little value
- unusually high dedupe hit rate may indicate unstable producer identity or excessive repeated noise

### 3.3 Cooldown hit rate

Question answered:

- does `cooldown_key` materially reduce repeated summaries within the observation window

Evidence to capture:

- number of cooldown suppressions
- cooldown hit rate = cooldown suppressions / emitted-or-suppressed candidate entries

Suggested interpretation:

- near-zero cooldown activity suggests weak practical value
- high cooldown activity suggests possible benefit, but also raises the question of whether the upstream producer is too chatty

### 3.4 Recovery ratio

Question answered:

- does `recovery_of` produce useful closure, or mostly add extra internal chatter

Evidence to capture:

- number of `recovery_of` candidates seen
- number of recovery summaries actually emitted
- recovery ratio = emitted recovery summaries / total emitted shadow summaries

Suggested interpretation:

- a low but meaningful recovery ratio can be healthy
- a high recovery ratio paired with low decision value may indicate churn rather than useful signal

### 3.5 False positive / noise indicators

Question answered:

- does the prototype produce shadow summaries that do not help a human make a better decision

Evidence to capture:

- count of summaries later judged non-actionable even as internal context
- count of summaries that repeat information already obvious from canonical SSOT or formal alerting
- count of summaries where text appears ambiguous enough to risk misreading as a real alert

Suggested interpretation:

- repeated ambiguity or duplication is retirement pressure
- low-noise internal summaries are a prerequisite for any future upgrade discussion

### 3.6 Decision value

Question answered:

- did the prototype help a reviewer understand a situation faster or more accurately

Evidence to capture:

- count of summaries judged to provide net-new context
- short reviewer note for each net-new context event
- count of summaries judged to add no new value

Decision value rule:

- “interesting” is not enough
- the evidence must show that the summary improved operator or reviewer understanding beyond canonical SSOT plus existing formal alerting

### 3.7 Canonical overlap

Question answered:

- how often does the prototype merely restate existing canonical or formal alert information

Evidence to capture:

- count of summaries that map directly to already-visible canonical SSOT state
- count of summaries that map directly to already-visible formal alert output
- overlap ratio = overlap count / total emitted shadow summaries

Suggested interpretation:

- high overlap is strong retirement pressure
- low overlap does not by itself justify upgrade; it only shows the path might be adding distinct context

## 4. Collection Sources And Format

Allowed evidence sources:

- process-local runtime log lines from the default-off prototype during a deliberate manual observation session
- local inspection of:
  - `reports/state_atomic/alerts_latest.json`
  - `reports/state_atomic/alerts_journal.jsonl`
- manual comparison against canonical SSOT surfaces for validation only:
  - `data/state/system_health_latest.json`
  - `data/state/daily_report_latest.json`
  - existing operator-visible formal alert outputs, if relevant
- future docs audit notes or PR notes summarizing the observation window

Forbidden evidence sinks:

- `data/state/*`
- any new repo-tracked runtime log
- any new canonical summary file
- any new steward-written artifact under `reports/state_atomic/*`

Boundary rule:

- evidence may be collected from local runtime logs and manual notes only
- evidence must not be re-materialized as canonical state
- evidence must not be used to back-fill `/status`, `/daily`, or `/dashboard`

Recommended evidence format:

- keep raw logs local and ephemeral
- summarize only distilled observations in Markdown inside a future review PR, issue, or architecture note
- do not commit generated runtime logs or sampled artifacts
- use `docs/templates/prototype_upgrade_review_template_v1.md` for future upgrade review
- use `docs/templates/prototype_retirement_review_template_v1.md` for future retirement review

Suggested observation ledger format:

| Session date | Prototype enabled manually | Candidate entries | Emitted shadow summaries | Dedupe suppressions | Cooldown suppressions | Recovery summaries | Canonical overlap | Decision value notes | Noise notes |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| YYYY-MM-DD | yes/no | 0 | 0 | 0 | 0 | 0 | 0 | short note | short note |

## 5. Observation Window And Review Cadence

Recommended observation strategy in v1:

- no always-on collection
- no schedule
- no launchd
- no 24/7 runtime capture
- only short manual observation sessions in a non-P0 context when a reviewer explicitly wants evidence

Recommended minimum observation window before any upgrade or retirement review:

- 14 calendar days
- and at least 5 manual observation sessions

Recommended review cadence:

1. mid-window check after roughly 7 days
2. end-window review after 14 days or after 5 sessions, whichever is later

If evidence is still thin at the end of the first window:

- extend once for another 14 days only if a reviewer believes meaningful signal is still plausible
- otherwise treat low signal as retirement pressure, not as an excuse for indefinite prototype drift

## 6. Review Ownership And Decision Responsibility

Evidence collection owner:

- the author of the future upgrade-review PR or retirement-review PR

Evidence reviewer:

- a human governance reviewer for the central steward path
- the reviewer must judge the evidence using documented criteria, not preference

Decision rule:

- the prototype itself does not score or judge its own evidence
- central steward does not write a decision artifact
- final judgment belongs in human-reviewed docs or PR discussion

## 7. Upgrade Review Trigger

An upgrade review may begin only when all of the following are evidenced:

- at least one completed observation window exists
- decision value is documented in multiple sessions, not just one anecdote
- confusion/noise remains low enough that internal reviewers believe a clearly labeled shadow summary would still be distinguishable from formal alerting
- canonical overlap is low enough that the prototype is not mostly restating existing truth
- the prototype remains default-off, internal-only, non-canonical, and fully stoppable throughout the observation window

Required next action if triggered:

- open a dedicated minimal PR for upgrade review only
- do not combine it with rollout, repair, or state-plane changes

## 8. Retirement Review Trigger

A retirement review should begin when one or more of the following is evidenced:

- the observation window shows low or zero decision value
- canonical overlap remains high
- false-positive or noise notes remain high
- reviewers repeatedly need extra wording to explain why the prototype is not a real alert
- the only way to justify the prototype is to blur the Stage 2 or Stage 7 boundary
- manual evidence collection itself costs more than the insight gained

Required next action if triggered:

- open a dedicated minimal retirement PR
- archive or remove the prototype path cleanly rather than letting it drift indefinitely

## 9. Degrade / Kill Switch / Removal Plan

Degrade:

- if no evidence is collected, nothing breaks
- the prototype remains optional and default-off
- `/status`, `/daily`, and `/dashboard` remain on canonical SSOT

Kill switch:

- keep `HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0` as the default
- if any manual evidence session is started, turn the flag back off immediately after the session
- if evidence collection begins creating confusion pressure, stop collecting and move directly to retirement review

Removal plan:

1. keep evidence collection local, manual, and review-scoped only
2. if retirement criteria are met, open a dedicated PR to retire the prototype path
3. do not mix retirement with unrelated central steward, state-plane, or Telegram changes

## 10. Recommended Strategy In v1

Current recommended strategy:

- keep the prototype in `Keep` status
- keep operational posture at `upgrade-observation only`
- collect evidence only through short manual observation sessions plus Markdown review notes
- do not add scheduled collection
- do not add new files under `data/state/*`
- do not add new canonical metrics or counters

Plain answer to the core question:

- collect evidence locally
- summarize it manually
- review after a fixed 14-day window with at least 5 sessions
- let a human governance reviewer decide whether the evidence supports upgrade review or retirement review

## 11. Canonical Answer

The canonical evidence collection answer in v1 is:

- collect only local, process-scoped, non-canonical evidence
- use Markdown summary tables rather than new runtime artifacts
- review on a fixed window instead of indefinite observation
- prefer retirement over ambiguity if the evidence never shows clear decision value
