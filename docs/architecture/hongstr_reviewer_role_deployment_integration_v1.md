# HONGSTR Reviewer Role Deployment Integration v1

## 1. Document Purpose

- This is the **HONGSTR Reviewer Role Deployment Integration v1**.
- The purpose of this document is to integrate the **Reviewer / Evidence Officer** role into the existing PR, governance, and adoption workflows in a **lightweight, non-blocking** manner.
- **This is NOT a final review authority spec.** It does not grant the Reviewer autonomous merge privileges.
- **This is NOT a runtime enforcement document.** It provides operational integration guidance only.

## 2. Reviewer Current Positioning

- **Advisory Status**: The Reviewer role is strictly a **review-only / proposal-only** participant.
- **Available Outputs**: The Reviewer is authorized to produce:
  - `Reviewer Note Draft`: General feedback and adherence checks.
  - `Evidence Sufficiency Memo`: Evaluating if ACs and logs map correctly to the code changes.
  - `Reopen Recommendation`: Suggesting that a PR be reopened or a gate be revisited based on missing evidence.
- **Limitations of Authority**:
  - The Reviewer is **NOT** the final merge authority.
  - The Reviewer is **NOT** the final runtime safety gate authority.
- **Handoff Requirement**: All conclusions reached by the Reviewer must be handed off to the Chief Steward, a Human Operator, or a stronger external reviewer path for final disposition.

## 3. Supported Trigger Scenarios

The Reviewer is expected to be called into action under the following scenarios:

- **Governance PRs**: When a PR involves blocker-reference governance, canonical docs, templates, examples, glossary updates, or index structure changes.
- **Canonical Wording**: When a PR involves canonical wording adjustments, alias retirement, or resolving source-role ambiguity.
- **Architectural Updates**: When a PR introduces a new role, updates to role contracts, adoption guidance, or governance cross-referencing.
- **Evidence Audits**: When a PR requires a preemptive evidence sufficiency check before reaching the human reviewer or Safety Gatekeeper.
- **Gate Status Checks**: When a PR requires a preliminary recommendation on whether to reopen an issue or "do-not-reopen" a closed governance discussion.

## 4. Unsupported / Prohibited Scenarios

The Reviewer **MUST NOT** be used to process or provide final judgments on the following:

- **Core Engine Mutations**: Final judgment on modifications to `src/hongstr`.
- **Truth-Source Edits**: Changes to `data/state/*` truth sources.
- **Runtime Integrity**: Changes to the `tg_cp` runtime execution plane.
- **Deployment Verdicts**: Final "go/no-go" deployment decisions.
- **Safety Blocks**: Final safety blocking decisions (these mandate deterministic script validation and human oversight).
- **Quant Conviction**: Final quantitative research conviction judgments or alpha selection.

## 5. Standard Output Formats

When integrated, the Reviewer will generate one of the following standardized artifacts:

### A. Reviewer Note Draft

- **When to use**: General PR hygiene checks, wording alignment, document sync.
- **Target Audience**: PR Author / Lead Implementation Engineer.
- **Status**: Proposal (Advisory).
- **Next Handoff**: PR Author for revision.

### B. Evidence Sufficiency Memo

- **When to use**: Evaluating whether attached logs, tests, or telemetry satisfies the PR's Acceptance Criteria.
- **Target Audience**: Safety Gatekeeper / Chief Steward / Human Reviewer.
- **Status**: Draft assessment.
- **Next Handoff**: Chief Steward / Human Reviewer to make the final Go/No-Go call.

### C. Reopen Gate Recommendation

- **When to use**: When evaluating whether a rejected PR addresses its previous failures, or if an issue needs to be unarchived.
- **Target Audience**: Governance Librarian / Chief Steward.
- **Status**: Proposal.
- **Next Handoff**: Governance Librarian / Chief Steward for final disposition.

### D. Insufficient Evidence Notice

- **When to use**: Immediate flag when a PR entirely lacks required artifacts (e.g., missing `guardrail_check.sh` output).
- **Target Audience**: PR Author.
- **Status**: Advisory block (flags for author to fix before human review).
- **Next Handoff**: PR Author.

## 6. Handoff & Escalation Rules

- **To the Author**: Routine missing evidence or format errors (`Reviewer Note`, `Insufficient Evidence Notice`).
- **To Governance Librarian**: Rule interpretations or reopen checks (`Reopen Recommendation`).
- **To Chief Steward / Human / Higher-Tier Model**: All evidence sufficiency memos, ambiguous findings, or high-risk assessments. The local Reviewer model defers upward.

## 7. Relationship to Existing Documents

- **Agent Roster**: Defines the strict boundary and mandate of the Reviewer persona.
- **Role × Model Fit Matrix**: Evaluates the risk and capability limits that constrain this role to a non-blocking capacity using existing local models (e.g., Qwen2.5/Coder).
- **Adoption-Facing Deployment Guidance**: Authorizes the Reviewer for "Phase B" (proposal-only) deployment.
- **This Document**: Acts strictly as the **integration layer**, detailing how the agent fits into the lifecycle of a PR. It does not overwrite enforcement stubs or landing document rules.

## 8. Deployment Level

This integration establishes the Reviewer at the following levels:

- **Read-only review aid**.
- **Proposal-only guidance**.
- **Checklist / PR guidance integration**.
*(It does not operate as a hard gate, nor does it possess autonomous review authority).*

## 9. Next Hand-Off

Following this integration document, the logical progression is:

- **Author/Reviewer Checklist Integration**: Updating the GitHub PR templates or local checklist stubs to formally request these Memos.
- **Lightweight Enforcement Guidance**: Creating the actual (read-only) script that generates the `Evidence Sufficiency Memo`.
- **Model Supplementation Trial Plan**: Testing external higher-tier models for complex multi-hop evidence review. *See [HONGSTR Reviewer Supplementation Advisory Trial v1](./hongstr_reviewer_supplementation_advisory_trial_v1.md)*.
*(Do not revert to wording adjustments or blocker-reference churn).*

---

### Appendix: Example Reviewer Output (Docs-Only)

*Note: This is an advisory note format, not an executable gate template.*

\`\`\`markdown
**[Reviewer Note Draft] Docs-Only PR Adherence**

- **AC Alignment**: Passed. PR includes only `.md` extensions. No core logic touched.
- **Governance Ref**: Cross-references Roster v1 successfully.
- **Recommendation**: Evidence sufficient for docs-only merge.
- **Handoff**: Routing to Chief Steward / Human Reviewer for final sign-off.
\`\`\`
