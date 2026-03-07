# HONGSTR Prototype Review Field Glossary v1

Last updated: 2026-03-07 (UTC+8)
Status: docs-first / glossary-first / governance-only
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: prototype review field glossary PR
Plane: central steward prototype review/package governance
Expected SSOT/output impact: none
Runtime impact: none (docs-only)
Rollout relation: governance-only; not rollout approval
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

This glossary standardizes the recurring fields and terms used across the central steward shadow/prototype review package.

Use it to answer:

- what a field means
- when a field should appear
- whether the field is required or optional
- which templates use it
- what common field drift or misuse to avoid

This glossary is governance-only.

It does not:

- authorize rollout
- authorize formal Telegram alerting
- change canonical SSOT
- change `/status`, `/daily`, or `/dashboard`
- change `tg_cp` runtime

Core rule:

- field alignment improves governance consistency only
- `glossary != rollout approval`

## 1. Scope

This glossary applies only to the prototype review/package chain around the current central steward shadow/prototype path.

It covers fields and terms used in:

- evidence summary
- upgrade-review
- retirement-review
- reviewer request-changes note
- decision record
- author and reviewer checklists
- resubmission checklist
- example packages

It does not define:

- canonical `data/state/*` schema
- `src/hongstr/**` runtime contracts
- Telegram message payloads
- rollout-specific runtime flags beyond boundary reminders already documented elsewhere

## 2. Field Rules

Read these rules before using any term below.

- Use the same field meaning across templates unless a template explicitly narrows it.
- Do not reinterpret a governance field as canonical system state.
- Do not reuse glossary fields as `/status`, `/daily`, or `/dashboard` truth.
- If a value is unknown, say `unknown` and explain why instead of inventing precision.
- If a field is not applicable, mark it clearly as `not applicable` rather than deleting it silently.

## 3. Glossary

### 3.1 `review_id`

- Definition: the unique identifier for one review or re-review record.
- When used: every live review template, request-changes note, decision record, and resubmission flow artifact.
- Templates using it:
  - `docs/templates/prototype_upgrade_review_template_v1.md`
  - `docs/templates/prototype_retirement_review_template_v1.md`
  - `docs/templates/prototype_review_decision_record_template_v1.md`
  - `docs/templates/prototype_review_request_changes_note_template_v1.md`
  - `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- Required or optional: required.
- Common misuse:
  - using a vague label like `prototype-review`
  - changing the ID mid-review without reason
  - omitting the review type or date component
- Example value: `prototype-upgrade-review-20260306`

### 3.2 `prototype_id`

- Definition: the stable slug for the prototype under review.
- When used: whenever the document must distinguish which prototype the package refers to.
- Templates using it:
  - `docs/templates/prototype_evidence_summary_template_v1.md`
  - `docs/templates/prototype_review_decision_record_template_v1.md`
- Required or optional: required where present; default value in v1 is fixed.
- Common misuse:
  - inventing a new slug for the same path
  - replacing the slug with human prose only
- Example value: `central-steward-shadow-prototype`

### 3.3 `review_type`

- Definition: the type of governance review being performed.
- When used: every review package and any related request-changes or decision record.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - decision record
  - request-changes note
  - author/reviewer/resubmission checklists
- Required or optional: required.
- Allowed values:
  - `upgrade-review`
  - `retirement-review`
  - `evidence-review` only where the template explicitly allows it
- Deprecated aliases:
  - `upgrade`
  - `retirement`
- Common misuse:
  - mixing `upgrade-review` and `retirement-review` in the same package
  - using a rollout label instead of a review label
  - switching label style inside one package without explanation
- Example value: `upgrade-review`

### 3.4 `review_window`

- Definition: the observation period the evidence is based on.
- When used: all substantive review artifacts and evidence summaries.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - decision record
- Required or optional: required for live reviews; optional only in reusable examples.
- Common misuse:
  - omitting dates after citing evidence
  - using vague terms like `recently`
  - using a different window in evidence summary and review template without explanation
- Example value: `2026-03-01..2026-03-14`

### 3.5 `reviewer`

- Definition: the human reviewer or governance reviewer responsible for examining the package.
- When used: all review-facing templates, request-changes notes, and decision records.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - reviewer checklist
  - decision record
  - request-changes note
- Required or optional: required.
- Common misuse:
  - leaving it blank in a final decision artifact
  - confusing reviewer with review author
- Example value: `hong`

### 3.6 `author`

- Definition: the person who assembled or resubmitted the review package.
- When used: author checklist, review templates, decision record, resubmission checklist, request-changes note.
- Templates using it:
  - evidence summary as `author`
  - upgrade-review template as `author`
  - retirement-review template as `author`
  - decision record as `author`
  - request-changes note as `author`
  - resubmission checklist as `author`
- Required or optional: required.
- Common misuse:
  - using reviewer and author interchangeably
  - omitting the author in a resubmission artifact
  - using deprecated alias `review_author` in new review packages
- Example value: `hong`

### 3.7 `evidence summary`

- Definition: the structured summary of observed evidence collected under the approved observation plan.
- When used: before or alongside any review template; often reused during resubmission.
- Templates using it:
  - `docs/templates/prototype_evidence_summary_template_v1.md`
  - referenced by all review templates, checklists, request-changes notes, and decision records
- Required or optional: required for `upgrade-review` and normal `retirement-review`; may be incomplete only when explicitly marked insufficient.
- Common misuse:
  - treating it as a final decision
  - writing free-form prose instead of structured fields
  - back-filling canonical state from it
- Example value: `prototype-central-steward-shadow-prototype-upgrade-review-20260301_20260314-evidence-summary.md`

### 3.8 `decision_value`

- Definition: how much net-new understanding the prototype added beyond canonical SSOT and formal alerting.
- When used: evidence summary and both review templates.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
- Required or optional: required.
- Common misuse:
  - equating “interesting” with decision value
  - claiming value without saying what changed for the reviewer/operator
- Example value: `low-value; repeated existing watchdog context without new diagnosis`

### 3.9 `canonical_overlap`

- Definition: how much the prototype output simply restates canonical SSOT or already-visible formal alerts.
- When used: evidence summary, `upgrade-review`, `retirement-review`, request-changes discussions.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
- Required or optional: required.
- Common misuse:
  - treating low overlap as automatic upgrade approval
  - not distinguishing overlap with SSOT versus overlap with formal alerts
- Example value: `medium; 3 of 7 summaries repeated existing watchdog state`

### 3.10 `false_positive_noise`

- Definition: summaries that did not improve understanding or that were ambiguous, repetitive, or operationally unhelpful. In prose this may still be described as false positive / noise, but the field label should stay `false_positive_noise`.
- When used: evidence summary and review templates, especially when deciding whether to keep or retire.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - resubmission checklist as a required re-check
- Required or optional: required where evidence is being evaluated.
- Common misuse:
  - counting all activity as noise
  - ignoring ambiguity risk because the path is still internal-only
  - replacing the canonical field label with ad hoc prose in structured tables
- Example value: `2 noisy summaries out of 6 because wording duplicated existing state without new context`

### 3.11 `recovery_of`

- Definition: the relationship between a recovery event and the earlier alert/event it closes; in review docs this usually appears as `recovery_of_ratio`.
- When used: evidence summary and review templates when assessing closure versus churn.
- Templates using it:
  - evidence summary as `recovery_of_ratio`
  - upgrade-review template as `recovery_of_ratio`
  - retirement-review template as `recovery_of_ratio`
- Required or optional: required in evidence fields where the ratio is listed; the direct raw field may be absent from docs if only the ratio is being reviewed.
- Common misuse:
  - treating every recovery as inherently useful
  - confusing the upstream alert relation with a final governance decision
- Example value: `recovery_of_ratio = 0.25`

### 3.12 `request_changes_reason`

- Definition: the normalized category explaining why a reviewer returned the package for fixes.
- When used: request-changes note and any resubmission work that closes the note.
- Templates using it:
  - `docs/templates/prototype_review_request_changes_note_template_v1.md`
  - referenced by `docs/templates/prototype_re_review_resubmission_checklist_v1.md`
- Required or optional: required when a request-changes note is issued.
- Governing record:
  - `docs/ops/prototype_request_changes_reason_alignment_record_v1.md`
- Allowed values:
  - `insufficient evidence`
  - `incomplete template`
  - `boundary unclear`
  - `rollout mixed into review PR`
  - `canonical overlap unclear`
  - `observation window incomplete`
  - `other`
- Common misuse:
  - using broad prose only with no fixed category
  - mixing several different blockers without naming them clearly
  - using prose aliases such as `missing evidence`, `boundary rewrite`, `rollout drift`, `canonical overlap not explained`, or `observation incomplete` instead of the canonical labels
  - treating reviewer response states such as `request-changes note required` or `return for fixes` as if they were request-changes reasons
  - treating `needs more evidence` as if it were the request-changes reason instead of the assessment-status label
- Example value: `boundary unclear`

### 3.13 `required fix label`

- Definition: the normalized label describing which concrete author-side fix must be completed after a request-changes note.
- When used: request-changes note, re-review resubmission checklist, reviewer guidance about blocker closure, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - resubmission example
- Required or optional: required where the docs structure blocker closure as named fix labels instead of freeform prose only.
- Governing record:
  - `docs/ops/prototype_required_fix_alignment_record_v1.md`
- Allowed values:
  - `missing evidence added`
  - `template completed`
  - `boundary wording clarified`
  - `rollout wording removed`
  - `canonical overlap explanation added`
  - `observation window extended`
- Common misuse:
  - using request-changes reasons such as `insufficient evidence` or `boundary unclear` as if they were required-fix labels
  - using prose-only completions such as `boundary wording rewritten`, `reviewer-facing boundary concerns are addressed`, or `observation window is complete` instead of the canonical labels
  - using next-action labels such as `extend evidence window` as if they were required-fix completion labels
- Example value: `boundary wording clarified`

### 3.14 `blocker closure status`

- Definition: the normalized per-blocker status used during resubmission to show whether a requested fix is done, not done, not applicable, or still unresolved.
- When used: re-review resubmission checklist, reviewer guidance for re-review, request-changes note closure tracking, and resubmission examples.
- Templates using it:
  - re-review resubmission checklist
  - request-changes note
  - reviewer checklist
  - resubmission example
- Required or optional: required where blocker items are tracked with explicit closure status instead of prose only.
- Governing record:
  - `docs/ops/prototype_blocker_closure_status_alignment_record_v1.md`
- Allowed values:
  - `completed`
  - `not completed`
  - `not applicable`
  - `unresolved`
- Common misuse:
  - using prose such as `closed`, `fully addressed`, or `materially unresolved` instead of the canonical labels
  - using combined shorthand such as `completed / not applicable` instead of one explicit status per blocker item
  - using required-fix labels or request-changes reasons as if they were blocker-closure-status labels
- Example value: `completed`

### 3.15 `blocker evidence reference`

- Definition: the normalized label for a field that points to the note, artifact, section, or link proving a blocker item, required fix, or re-review gate has supporting evidence.
- When used: request-changes note, re-review resubmission checklist, reviewer guidance for re-review, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where blocker proof is being captured with explicit links or references instead of prose only.
- Governing record:
  - `docs/ops/prototype_blocker_evidence_reference_alignment_record_v1.md`
- Allowed values:
  - `closure evidence reference`
  - `fix evidence reference`
  - `review note reference`
  - `supporting evidence reference`
- Common misuse:
  - using labels such as `request-changes closure note`, `evidence refresh note`, `re-review note`, or `updated evidence summary attached` as if they were interchangeable evidence-reference fields
  - using generic `attached or linked` prose where the blocker-specific evidence reference should be named explicitly
  - using raw target-hint prose such as `request-changes note / PR comment / review thread` or `updated evidence summary / review template / diff` instead of the canonical blocker-reference-target hint labels
  - using blocker-reference ordering hint labels as if they were blocker-evidence-reference labels themselves
  - using blocker-reference applicability hint labels as if they were blocker-evidence-reference labels themselves
  - using blocker-reference placeholder shapes as if they were blocker-evidence-reference labels themselves
  - using blocker-closure-status labels or required-fix labels as if they were evidence-reference labels
- Example value: `fix evidence reference = docs/reviews/prototype-central-steward-shadow/evidence-summary.md#canonical-overlap`

### 3.16 `blocker reference target hint`

- Definition: the normalized hint label describing what kind of link target should be supplied after a blocker-evidence-reference field.
- When used: request-changes note, re-review resubmission checklist, reviewer reminders about resubmission evidence links, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where the docs provide a placeholder or reminder for what kind of blocker-proof link should be pasted.
- Governing record:
  - `docs/ops/prototype_blocker_reference_target_hint_alignment_record_v1.md`
- Allowed values:
  - `PR comment link`
  - `evidence summary section link`
  - `template diff link`
  - `supporting doc link`
- Common misuse:
  - using prose such as `request-changes note / PR comment / review thread` instead of the normalized `PR comment link`
  - using broad mixed hints such as `updated evidence summary / template / diff` instead of naming `evidence summary section link` or `template diff link`
  - using raw singular/plural `link` or `links` where the doc should also declare the canonical blocker-reference multiplicity hint
  - using target-hint labels as if they were blocker-reference ordering hint labels
  - using target-hint labels as if they were blocker-reference applicability hint labels
  - using target-hint labels as if they were blocker-reference placeholder shapes
  - using target-hint labels as if they were blocker-evidence-reference labels themselves
- Example value: `review note reference = PR comment link`

### 3.17 `blocker reference multiplicity hint`

- Definition: the normalized hint label describing whether a blocker-evidence-reference field expects a single link, multiple links, or one-or-more links.
- When used: request-changes note, re-review resubmission checklist, reviewer reminders about resubmission evidence links, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where the docs provide a placeholder or reminder for how many blocker-proof links may be pasted.
- Governing record:
  - `docs/ops/prototype_blocker_reference_multiplicity_hint_alignment_record_v1.md`
- Allowed values:
  - `single link`
  - `multiple links`
  - `one-or-more links`
- Common misuse:
  - using bare `link` or `links` without the canonical multiplicity hint label
  - using prose such as `plus any needed` instead of the normalized `one-or-more links`
  - using multiplicity hints as if they were blocker-reference ordering hint labels
  - using multiplicity hints as if they were blocker-reference applicability hint labels
  - using multiplicity hints as if they were blocker-reference placeholder shapes
  - using multiplicity hints as if they were blocker-evidence-reference labels or blocker-reference-target hint labels
- Example value: `fix evidence reference = one-or-more links + evidence summary section link / template diff link`

### 3.18 `blocker reference ordering hint`

- Definition: the normalized hint label describing the order to present grouped blocker-evidence-reference fields when more than one appears in the same local list, reminder, or example.
- When used: request-changes note, re-review resubmission checklist, reviewer reminders about resubmission evidence links, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where the docs provide a reminder for sequencing multiple blocker-proof references.
- Governing record:
  - `docs/ops/prototype_blocker_reference_ordering_hint_alignment_record_v1.md`
- Allowed values:
  - `review note first`
  - `closure evidence next`
  - `fix evidence next`
  - `supporting evidence last`
- Common misuse:
  - leaving the grouped blocker-proof order implicit when multiple blocker-evidence-reference fields are shown together
  - putting `supporting evidence reference` ahead of the governing `review note reference` or ahead of closure/fix proof in a grouped list
  - using ordering hints as if they were blocker-reference applicability hint labels
  - using ordering hints as if they were blocker-reference placeholder shapes
  - using ordering hints as if they were blocker-evidence-reference labels, blocker-reference-target hint labels, or blocker-reference multiplicity hint labels
- Example value: `blocker evidence references = review note first + closure evidence next + fix evidence next + supporting evidence last`

### 3.19 `blocker reference applicability hint`

- Definition: the normalized hint label describing when a blocker-evidence-reference field should be filled versus when it may remain blank in the current local context.
- When used: request-changes note, re-review resubmission checklist, reviewer reminders about resubmission evidence links, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where the docs provide a reminder about when blocker-proof references should be present or may be left blank.
- Governing record:
  - `docs/ops/prototype_blocker_reference_applicability_hint_alignment_record_v1.md`
- Allowed values:
  - `if applicable`
  - `when requested`
  - `if present`
  - `only when closure proof exists`
- Common misuse:
  - leaving blocker-proof applicability implicit when a field may be omitted in one flow and required in another
  - using broad prose such as `applicable`, `as applicable`, or `if available` instead of the canonical applicability hint labels
  - using applicability hints as if they were blocker-reference placeholder shapes
  - using applicability hints as if they were blocker-evidence-reference labels, blocker-reference-target hint labels, blocker-reference multiplicity hint labels, or blocker-reference ordering hint labels
- Example value: `closure evidence reference = only when closure proof exists`

### 3.20 `blocker reference placeholder shape`

- Definition: the normalized display shape used to render a blocker-evidence-reference field together with its applicability hint, ordering hint, and angle-bracket placeholder.
- When used: request-changes note, re-review resubmission checklist, reviewer reminders about resubmission evidence links, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where the docs provide a concrete blocker-proof placeholder block rather than prose only.
- Governing record:
  - `docs/ops/prototype_blocker_reference_placeholder_shape_alignment_record_v1.md`
- Canonical placeholder-shape parts:
  - `Applicability hint: ...`
  - `Ordering hint: ...`
  - `<single link: ...>`
  - `<multiple links: ...>`
  - `<one-or-more links: ...>`
- Common misuse:
  - using inline `field: <...>` placeholder shapes where the canonical stacked field block should be used
  - omitting `Applicability hint:` or `Ordering hint:` from a field block while still relying on those semantics
  - treating placeholder shape parts as if they were blocker-evidence-reference labels or hint-label enums
- Example value: `Review note reference:` + `Applicability hint: if present` + `Ordering hint: review note first` + `<single link: PR comment link>`

### 3.21 `blocker reference field caption formatting`

- Definition: the normalized displayed caption formatting used for blocker-evidence-reference field names in stacked field blocks and example snippets.
- When used: request-changes note, re-review resubmission checklist, reviewer reminders about resubmission evidence links, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where the docs display blocker-evidence-reference field captions as standalone caption lines.
- Governing record:
  - `docs/ops/prototype_blocker_reference_field_caption_casing_alignment_record_v1.md`
- Canonical field captions:
  - `Review note reference:`
  - `Closure evidence reference:`
  - `Fix evidence reference:`
  - `Supporting evidence reference:`
- Formatting rule:
  - use sentence case, not title case
  - capitalize the first word only
  - keep the trailing colon
  - do not abbreviate the caption
- Common misuse:
  - using lowercase caption forms such as `review note reference:`
  - dropping the trailing colon from a displayed blocker-reference field caption
  - abbreviating captions such as `review note ref:`
  - treating caption formatting as if it were the blocker-evidence-reference label, target hint label, multiplicity hint label, ordering hint label, applicability hint label, placeholder shape, or rendering rule
- Example value: `Review note reference:`

### 3.22 `blocker reference rendering rule`

- Definition: the normalized rule describing when a blocker-evidence-reference field may appear as an explanatory inline fragment and when it must be rendered as a stacked multi-line field block.
- When used: request-changes note, re-review resubmission checklist, reviewer reminders about resubmission evidence links, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where the docs distinguish explanatory placeholder prose from live blocker-evidence-reference field rendering.
- Governing record:
  - `docs/ops/prototype_blocker_reference_rendering_exception_alignment_record_v1.md`
- Canonical rendering rules:
  - `inline placeholder-only fragment allowed in explanatory prose`
  - `stacked field block required for live blocker-evidence-reference fields`
  - `compact inline form allowed only in explanatory prose or a compact table cell`
  - `expand to multi-line block when field caption or hint lines are shown`
- Common misuse:
  - treating inline `field: <...>` examples as if they were the canonical live field rendering
  - treating bare angle-bracket placeholders as if they were a complete live blocker-evidence-reference field
  - saying inline form is acceptable without stating that it is limited to explanatory prose or a compact table cell
  - treating rendering rules as if they were field-caption formatting, live-field cue phrases, evidence-reference labels, target hint labels, multiplicity hint labels, ordering hint labels, applicability hint labels, or placeholder shapes
- Example value: `live blocker-evidence-reference field -> stacked field block required for live blocker-evidence-reference fields`

### 3.23 `blocker reference live-field cue phrase`

- Definition: the normalized cue phrase used to tell the reader that the current blocker-evidence-reference item is an actual live field to fill or inspect, rather than explanatory prose only.
- When used: request-changes note, re-review resubmission checklist, reviewer reminders about resubmission evidence links, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where the docs need to distinguish a real fillable blocker-proof field from explanatory inline placeholder prose.
- Governing record:
  - `docs/ops/prototype_blocker_reference_live_field_cue_alignment_record_v1.md`
- Canonical cue phrases:
  - `live blocker-evidence-reference field`
  - `live fill-in field`
  - `live field block`
- Cue rule:
  - use `live blocker-evidence-reference field` as the primary cue phrase
  - use `live fill-in field` when the local sentence is emphasizing fillability
  - use `live field block` when the local sentence is emphasizing the rendered stacked block form
- Common misuse:
  - using broad phrases such as `live field` or `actual field to fill` instead of the canonical cue phrases
  - switching between `entry` and `field` with no stable cue rule
  - treating live-field cue phrases as if they were explanatory-inline cue phrases, rendering rules, field-caption formatting, evidence-reference labels, target hint labels, multiplicity hint labels, ordering hint labels, applicability hint labels, or placeholder shapes
- Example value: `render the live blocker-evidence-reference field as a live field block`

### 3.24 `blocker reference explanatory-inline cue phrase`

- Definition: the normalized cue phrase used to tell the reader that the current blocker-reference wording is explanatory-only and not a live field to fill.
- When used: request-changes note, re-review resubmission checklist, reviewer reminders about resubmission evidence links, author reminders for resubmission, and resubmission examples.
- Templates using it:
  - request-changes note
  - re-review resubmission checklist
  - reviewer checklist
  - author checklist
  - resubmission example
- Required or optional: required where the docs need to distinguish explanatory-only blocker-reference wording from a live blocker-evidence-reference field.
- Governing record:
  - `docs/ops/prototype_blocker_reference_explanatory_inline_cue_alignment_record_v1.md`
- Canonical cue phrases:
  - `explanatory prose`
  - `compact table cell`
  - `inline placeholder-only fragment`
- Cue rule:
  - use `explanatory prose` as the primary non-live cue phrase
  - use `compact table cell` when the non-live explanation is compressed into one small table cell
  - use `inline placeholder-only fragment` when the non-live wording is only the bare angle-bracket placeholder snippet
  - keep these cue phrases distinct from `live blocker-evidence-reference field`, `live fill-in field`, and `live field block`
- Common misuse:
  - using `reminder prose`, `table-cell reminder`, or `inline fragment` instead of the canonical cue phrases
  - treating explanatory-inline cue phrases as if they were live-field cue phrases, rendering rules, field-caption formatting, evidence-reference labels, target hint labels, multiplicity hint labels, ordering hint labels, applicability hint labels, or placeholder shapes
- Example value: `use inline placeholder-only fragment only in explanatory prose`

### 3.25 `assessment status`

- Definition: the provisional evidence-summary posture recorded before a final review decision exists.
- When used: evidence summary and package assembly examples when the docs are still expressing review readiness rather than a final outcome.
- Templates using it:
  - evidence summary
  - package example notes
- Required or optional: required where a template includes an explicit assessment-status field.
- Governing record:
  - `docs/ops/prototype_assessment_status_alignment_record_v1.md`
- Allowed values:
  - `continue observation`
  - `candidate for upgrade-review`
  - `candidate for retirement-review`
  - `needs more evidence`
- Common misuse:
  - using `keep` as a preliminary assessment label instead of the canonical observation posture
  - using `insufficient evidence` as a preliminary assessment label instead of `needs more evidence`
  - treating `candidate for upgrade-review` or `candidate for retirement-review` as final decision outcomes
  - leaving the field unlabeled so assessment status, decision outcome, and next action blur together
- Example value: `continue observation`

### 3.26 `reviewer response state`

- Definition: the normalized reviewer-side workflow state used when the package is being returned, gated for re-review, or handed off to the final decision record.
- When used: reviewer checklist, request-changes note, resubmission flow, and resubmission example.
- Templates using it:
  - reviewer checklist
  - request-changes note
  - re-review resubmission checklist
  - resubmission example
- Required or optional: required where a template includes an explicit reviewer response-state field or response-state guardrail note.
- Governing record:
  - `docs/ops/prototype_reviewer_response_state_alignment_record_v1.md`
- Allowed values:
  - `request-changes note required`
  - `return for fixes`
  - `re-review allowed after fixes`
  - `ready for decision record`
- Common misuse:
  - using `request changes` or `request-changes note` as if they were the response-state label itself
  - using `insufficient evidence for decision` as a reviewer response-state enum instead of request-changes reason or decision outcome wording
  - putting reviewer response states inside the final decision outcome enum
  - leaving the state implied by prose only when a structured label is available
- Example value: `ready for decision record`

### 3.27 `decision outcome`

- Definition: the fixed governance result recorded after review or re-review.
- When used: reviewer checklist, decision record, and review templates.
- Templates using it:
  - reviewer checklist
  - decision record
  - upgrade-review
  - retirement-review
- Required or optional: required in final decision artifacts.
- Allowed values:
  - `keep`
  - `upgrade-review pass`
  - `upgrade-review fail`
  - `retirement-review pass`
  - `retirement-review fail`
  - `insufficient evidence`
- Common misuse:
  - inventing a new status like `soft pass`
  - treating `request changes` as a final decision outcome instead of a return-for-fixes state
  - treating reviewer response states such as `request-changes note required`, `return for fixes`, `re-review allowed after fixes`, or `ready for decision record` as final decision outcomes
  - treating `continue observation` or `needs more evidence` as final decision outcomes instead of assessment status or next action
  - treating assessment-only labels like `candidate for upgrade-review` or `candidate for retirement-review` as final decision outcomes
  - combining `insufficient evidence` with `continue observation` into one pseudo-enum
- Example value: `keep`

### 3.28 `next action`

- Definition: the smallest allowed follow-on step after the current review state or decision.
- When used: evidence summary, review templates, decision record, reviewer notes.
- Templates using it:
  - evidence summary
  - upgrade-review
  - retirement-review
  - decision record
  - reviewer checklist
- Required or optional: required where the template includes an explicit action block.
- Governing record:
  - `docs/ops/prototype_decision_next_action_alignment_record_v1.md`
- Allowed values:
  - `continue observation`
  - `extend evidence window`
  - `open review PR`
  - `open retirement PR`
  - `no action`
- Common misuse:
  - using rollout language inside a review-only artifact without separate approval
  - using stage-specific prose like `open upgrade review`, `open retirement review`, or `open rollout candidate PR` instead of the canonical labels
  - skipping the action even when the decision is recorded
- Example value: `continue observation`

### 3.29 `boundary check labels`

- Definition: the canonical wording used for structured boundary-check rows, field labels, and checklist labels across the prototype review/package docs.
- When used: evidence summary, upgrade-review, retirement-review, decision record, author checklist, reviewer checklist, resubmission checklist, and examples.
- Governing record:
  - `docs/ops/prototype_boundary_check_row_alignment_record_v1.md`
- Canonical labels:
  - `internal-only`
  - `not-canonical`
  - does not affect `/status`
  - does not affect `/daily`
  - does not affect `/dashboard`
  - does not write `data/state/*`
  - does not create a second state writer
  - does not change `tg_cp` runtime
  - does not touch bounded repair
  - `review PR != rollout PR`
- Common misuse:
  - mixing `affects`, `does not change`, and `no impact` for the same boundary
  - adding `truth` to `/dashboard` in some files but not others
  - padding the same label with `still`, `remains`, or `at review time` inside structured rows
  - using `touches tg_cp runtime` instead of the normalized runtime-impact label
  - using `not a rollout PR` in one checklist and `disguised rollout PR` in another without the shared canonical label
- Example value: does not affect `/status`

## 4. Common Drift To Avoid

Do not let any of these drift patterns enter the package:

- using `reviewer`, `author`, and `review_author` inconsistently without context
- changing enum labels between templates
- using ad hoc blocker-proof labels instead of the canonical blocker-evidence-reference labels
- using ad hoc link-target prose instead of the canonical blocker-reference-target hint labels
- using ad hoc singular/plural link prose instead of the canonical blocker-reference multiplicity hint labels
- using ad hoc blocker-proof ordering prose instead of the canonical blocker-reference ordering hint labels
- using ad hoc blocker-proof applicability prose instead of the canonical blocker-reference applicability hint labels
- using ad hoc blocker-reference placeholder formatting instead of the canonical placeholder shape
- using ad hoc blocker-reference caption case, punctuation, or abbreviations instead of the canonical field-caption formatting
- using ad hoc inline-vs-stacked blocker-reference rendering prose instead of the canonical rendering rules
- using ad hoc blocker-reference live-field cue wording instead of the canonical cue phrases
- using ad hoc blocker-reference explanatory-inline cue wording instead of the canonical non-live cue phrases
- using `decision_value` as a synonym for “I like this”
- using `canonical_overlap` without saying what it overlaps with
- using `request changes` prose without a fixed reason category
- turning glossary terms into rollout or canonical state language

## 5. Non-Rollout Reminder

Interpret this glossary correctly:

- it standardizes documentation terms only
- it does not approve runtime rollout
- it does not change canonical SSOT
- it does not change `/status`, `/daily`, or `/dashboard`

## 6. Canonical Answer

The canonical v1 answer is:

- use one shared meaning for recurring review fields
- keep enum values fixed
- mark required versus optional consistently
- call out common misuse early
- treat this glossary as governance alignment only, never as rollout approval
