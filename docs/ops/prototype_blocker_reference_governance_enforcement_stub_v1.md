# HONGSTR Prototype Blocker-Reference Governance Enforcement Stub v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / adoption-first / enforcement-stub-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype blocker-reference read-only governance enforcement stub PR
Plane: central steward prototype review/package governance
Expected SSOT/output impact: none
Runtime impact: none (docs-only / read-only guidance only)
Rollout relation: non-blocking guidance only; not rollout approval
Kill switch: HONGSTR_TG_ALERT_INGEST_PROTOTYPE=0
Canonical truth boundary: does not change canonical SSOT or `/status` `/daily` `/dashboard`; does not write `data/state/*`

Boundary reminder:

- This document is not a rollout authorization.
- This document does not authorize formal Telegram alerting.
- This document is not canonical SSOT.
- This document does not change `/status` `/daily` `/dashboard` truth sources.
- This document does not permit writes to `data/state/*`.
- This document has no runtime wiring effect.
- This document does not authorize bounded repair.

## 0. Purpose

This document is a read-only governance enforcement stub for the prototype blocker-reference docs/governance line.

Its purpose is to:

- establish one non-blocking adoption/review/reopen entrypoint after Phase A closure
- tell authors, reviewers, and agents where the canonical source-of-truth docs live
- state which drift classes are no longer accepted for reopen
- define the reopen gate for any future blocker-reference PR
- hand this line off toward adoption, governance enforcement, and the smallest safe runtime-facing bridge

This stub is:

- read-only guidance only
- non-blocking
- usable from PR guidance, checklist guidance, and review guidance

This stub is not:

- runtime enforcement
- CI hard-fail enforcement
- an auto-rewriter
- rollout approval
- a change to canonical SSOT or `/status` `/daily` `/dashboard`

If future work wants stronger enforcement than this stub, it must open a separate evidence-backed PR.

## 1. Scope

This stub currently covers only the blocker-reference docs/governance line inside the prototype review/package chain.

It does not change or govern:

- `src/hongstr/**`
- `scripts/refresh_state.sh`
- `scripts/state_snapshots.py`
- `data/state/*`
- `tg_cp` runtime
- bounded repair
- formal Telegram alerting
- rollout wiring

Scope rule:

- this stub exists to route human and agent behavior toward the landed blocker-reference governance docs
- it does not perform checks by itself
- it does not block CI, mutate files, or publish runtime truth

## 2. Canonical Source-Of-Truth

Use the blocker-reference docs in this source-role split:

- Landing doc
  Role: closure map, completed canonical-layer inventory, alias/drift retirement posture, and reopen gate baseline.
  Source: `docs/ops/prototype_blocker_reference_governance_landing_v1.md`
- Glossary
  Role: primary term-level source of truth for vocabulary, field-split boundaries, and canonical concept names.
  Source: `docs/ops/prototype_review_field_glossary_v1.md`
- Alignment records
  Role: layer-specific drift-to-canonical mapping for already-landed blocker-reference layers; use only when the landing doc and glossary point you to a specific layer.
  Sources: the blocker-reference alignment records named in the landing doc.
- Templates
  Role: live author/reviewer fill surfaces for request-changes, resubmission, reviewer review, and author pre-submit flow.
  Sources:
  `docs/templates/prototype_review_request_changes_note_template_v1.md`
  `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
  `docs/templates/prototype_review_reviewer_checklist_v1.md`
  `docs/templates/prototype_review_pr_author_checklist_v1.md`
- Examples
  Role: assembled demonstrations of canonical usage; examples illustrate the rules but do not override glossary or landing doc decisions.
  Sources:
  `docs/examples/prototype_review_package_example_v1.md`
  `docs/examples/prototype_resubmission_example_v1.md`
- Index
  Role: routing entrypoint that tells future authors/reviewers which document to read first.
  Source: `docs/ops/prototype_review_package_index_v1.md`
- This enforcement stub
  Role: read-only adoption, review-entry, and reopen-guidance surface after Phase A closure.
  Source: `docs/ops/prototype_blocker_reference_governance_enforcement_stub_v1.md`

Canonical-source rule:

- use the landing doc to decide whether the blocker-reference line should be reopened at all
- use the glossary to decide what a blocker-reference term or layer means
- use the relevant alignment record only when a specific layer needs drift-to-canonical confirmation
- use templates and examples to apply the already-landed rules without inventing new wording
- use this stub to keep human/agent behavior read-only and non-blocking

## 3. Review / Author / Agent Usage

Use this flow whenever a PR touches blocker-reference wording, formatting, placement, or related guidance:

1. read `docs/ops/prototype_blocker_reference_governance_landing_v1.md`
2. confirm whether the issue is a real reopen candidate or just wording churn
3. read `docs/ops/prototype_review_field_glossary_v1.md` for the term/layer boundary
4. read the relevant template/example/index surface where the wording would actually be used
5. open a new blocker-reference PR only if the reopen gate in Section 4 is met

Role-specific rule:

- Author
  Use the landing doc and this stub before proposing blocker-reference wording changes. If the change is only alias churn, do not reopen.
- Reviewer
  Use this stub to reject wording-only churn and route the author back to the landing doc and glossary.
- Agent
  Use this stub as the non-blocking governance entrypoint before touching blocker-reference docs. Do not expand scope into runtime or CI enforcement through this doc alone.

## 4. Reopen Gate

Reopen this blocker-reference line only when at least one of these is true:

- a genuinely new blocker-reference concept layer appears that the landing doc does not already list
- there is a real source-role ambiguity between landing doc, glossary, alignment record, template, example, or index
- a Phase B adoption/enforcement/minimal runtime-facing bridge needs one new governance artifact because the current docs are insufficient
- a reviewer/author/agent cannot apply the current blocker-reference rules without inventing a new concept, not merely a new synonym

Do not reopen when the request is only:

- alias churn
- wording preference churn
- casing, punctuation, or placement reshuffling already covered by landed layers
- another finer split of an already-closed blocker-reference concept layer
- a request to restate the same short example, intro phrase, or contrast sentence without a new concept

Reopen-note rule:

- any future PR that reopens this line should cite the exact reopen gate it satisfies
- if no reopen gate can be named concretely, the PR should not be opened

## 5. Drift Classes No Longer Accepted

These blocker-reference drift classes should now be treated as rejected churn rather than valid reopen triggers:

- reintroducing retired aliases after a layer already has a canonical answer
- changing canonical short examples without adding a new concept layer
- re-litigating short-example labels, placement, punctuation, or block-intro phrases already fixed by landed records
- mixing live-field cue, explanatory-inline cue, rendering rule, and contrast rule back into one blended prose change
- inventing alternate source roles when landing doc and glossary already split the roles clearly

If one of those patterns appears, the guidance answer should be:

- point back to the landing doc
- point back to the glossary or relevant record
- do not reopen the blocker-reference wording line

## 6. Enforcement Level

Current enforcement level:

- read-only guidance only
- non-blocking stub
- usable from reviewer checklist, author checklist, package index, landing doc, or examples as a routing note
- not CI hard gate
- not runtime enforcement
- not an auto-fix mechanism

Enforcement rule:

- this stub may be cited in PR guidance, review guidance, or docs guidance
- any future upgrade to CI checks, bot comments, scripted linting, or runtime wiring requires a separate evidence-backed PR

## 7. Handoff Note

This document is the Phase B kickoff stub for the blocker-reference governance line.

The next step should not be more wording micro-splitting.

The next step should move toward one of these adoption/enforcement directions:

- read-only governance adoption guidance used consistently by authors, reviewers, and agents
- a minimal governance-enforcement bridge that stays non-invasive and preserves Stage 2 / Stage 7 / Stage 8 boundaries
- a minimal runtime-facing bridge only if it remains read-only, non-canonical, and separately evidence-backed

Handoff rule:

- treat the blocker-reference docs line as a Phase A closure candidate that now hands off into Phase B adoption/enforcement work
- unless a new concept layer or real source-role ambiguity appears, do not continue splitting blocker-reference wording PRs

## 8. Canonical Answer

Yes. After Phase A closure, the next correct move is a non-blocking read-only governance enforcement stub, not another blocker-reference wording alignment PR. Canonical blocker-reference rules remain in the landing doc, glossary, layer records, templates, examples, and index; this stub only routes adoption, review, and reopen behavior toward those sources.
