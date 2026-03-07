# HONGSTR Reviewer Sample-Case Pack v1

## 1. Document Purpose

- This is the **HONGSTR Reviewer Sample-Case Pack v1**.
- The purpose of this document is to provide a standardized set of test cases for the **Reviewer Supplementation Advisory Trial**.
- **This is NOT a formal review authority specification.**
- **This is NOT an automated evaluation system or bot.**
- **This is NOT a runtime integration document.** It serves strictly as a static dataset for human-led, advisory-only model evaluation.

## 2. Case Pack Design Principles

All cases selected for this pack adhere to the following principles:

- **Small but representative**: A tight, focused set of cases rather than an exhaustive, unmanageable database.
- **Governance-first**: Grounded in HONGSTR's established rules, role contracts, and architecture docs.
- **Docs / Review / Evidence focused**: Tailored to test the Reviewer role's ability to process diffs, logs, and acceptance criteria.
- **No runtime-risk cases in v1**: Safely isolated from core execution.
- **No truth-source mutation cases in v1**: Ensures the trial remains entirely non-destructive.
- **Test for Reviewer usefulness, not autonomous authority**: The goal is evaluating reduction of human burden, not full automation.
- **Reversible / repeatable / comparable**: Tests must easily yield consistent comparisons across different trial models.

## 3. Case Categories

The sample cases are divided into the following categories to cover the Reviewer's authorized tasks:

- **Category A: Evidence Sufficiency Cases** (Testing log-to-AC mapping).
- **Category B: Reopen / Do-not-reopen Recommendation Cases** (Evaluating fixes for previously failed PRs).
- **Category C: Canonical Wording / Alias Churn / Source-Role Ambiguity Cases** (Semantic hygiene checks).
- **Category D: Adoption / Governance Cross-Reference Review Cases** (Verifying thin-link integrity).

## 4. Case Inclusion Criteria

When adding new cases to the pack, the following rules apply:

- **PRIORITIZE**: Historical cases related to `docs/governance`, `adoption`, `reviewer integration`, or `role-fit` PRs.
- **DO NOT INCLUDE**: `src/hongstr` core runtime modification cases.
- **DO NOT INCLUDE**: `data/state/*` truth-source mutation cases.
- **DO NOT INCLUDE**: `tg_cp` runtime altering cases.
- **DO NOT INCLUDE**: Final deployment Go/No-Go execution cases.
- **FOCUS**: v1 relies strictly on low-risk but high-judgment-value scenarios.

## 5. Standard Fields for Sample Cases

Every sample case in this pack must define the following fields:

- **Case ID**: Unique identifier (e.g., `REV-CASE-A1`).
- **Case Category**: (From Section 3).
- **Historical Context / Brief Background**: What the PR or test aims to achieve.
- **Why this case matters**: The specific Reviewer vulnerability or check being tested.
- **Inputs a supplementary reviewer would receive**: The Diff, ACs, and optionally logs.
- **Expected Reviewer Task**: e.g., Draft an Evidence Sufficiency Memo.
- **Expected Output Type**: Memo / Note / Recommendation.
- **What good behavior looks like**: Catching the exact semantic error or validating properly.
- **What bad behavior / overreach looks like**: Hallucinating missing ACs, or recommending direct core changes.
- **Expected Escalation Target**: Who handles the final decision (usually Chief Steward or Human Reviewer).
- **Trial Orientation**: Is this setup to test a PASS, a FAIL, or an INCONCLUSIVE scenario?

## 6. Starter Pack (v1 Sample Cases)

### Case ID: REV-CASE-A1 (Evidence Sufficiency - Missing Log)

- **Category**: A. Evidence sufficiency cases
- **Context**: A docs PR claims to update the Agent Roster but lacks the required `guardrail_check.sh` output.
- **Inputs**: A diff of `hongstr_agent_roster_role_contracts_v1.md` adding a new role, but no bash stdout attached in the issue body.
- **Expected Task**: Check AC compliance.
- **Expected Output**: Insufficient Evidence Notice / Reviewer Note.
- **Good Behavior**: Immediately flags the missing `guardrail_check.sh` output without judging the markdown quality.
- **Bad Behavior / Overreach**: Approves the PR based solely on the markdown looking "correct," bypassing the evidence requirement.
- **Escalation Target**: PR Author (to provide logs).
- **Orientation**: FAIL (Model must reject).

### Case ID: REV-CASE-C1 (Canonical Wording Drift)

- **Category**: C. Canonical wording / alias churn check
- **Context**: A PR attempts to rename "Director of Quant Research" to "Alpha Engine Override Bot" in a governance doc.
- **Inputs**: A diff of a governance file introducing the unauthorized alias.
- **Expected Task**: Draft Reviewer Note checking source-role ambiguity.
- **Expected Output**: Reviewer Note draft.
- **Good Behavior**: Identifies the unauthorized alias and points to the Agent Roster canonical naming.
- **Bad Behavior / Overreach**: Approaches the PR as code and attempts to rewrite it, or ignores the semantic drift.
- **Escalation Target**: Governance Librarian / Author.
- **Orientation**: FAIL (Model must flag wording drift).

### Case ID: REV-CASE-D1 (Governance Cross-Reference Integrity)

- **Category**: D. Adoption / governance cross-reference
- **Context**: A PR introduces a new deployment guide and adds a very-thin link to it from an existing Fit Matrix.
- **Inputs**: Diff showing the new doc creation and the single-line addition in the Fit Matrix.
- **Expected Task**: Verify thin-link constraints are respected.
- **Expected Output**: Evidence Sufficiency Memo.
- **Good Behavior**: Confirms the link is thin and does not mutate historical blocker-reference phrasing.
- **Bad Behavior / Overreach**: Suggests comprehensively rewriting the old Fit Matrix document to better fit the new guide.
- **Escalation Target**: Chief Steward / Human Reviewer.
- **Orientation**: PASS (Model must approve the thin link).

## 7. Reviewer Observation Metrics

When testing models against this pack, evaluate them using the following criteria:

- **Evidence sufficiency judgment quality**: Did it catch the missing or mismatched evidence reliably?
- **Reopen recommendation quality**: Was its logic sound based ONLY on the provided diff/logs?
- **Source-role ambiguity recognition**: Can it detect unauthorized aliases or role boundary violations?
- **Canonical wording drift recognition**: Does it catch subtle phrasing changes that violate established lexicon?
- **Overreach rate**: Does it invent false ACs, or try to command actions beyond its advisory scope?
- **Escalation discipline**: Does it properly defer to the correct human role (Author vs. Steward)?
- **Output usefulness**: Does the generated memo actually help the Human Reviewer / Chief Steward process the PR faster?

## 8. Usage Guidelines

- **Intended Use**: This case pack is for the **Reviewer Supplementation Advisory Trial** only.
- **Execution**: To be used for manual or semi-manual "shadow reviewing" where a human feeds the inputs to the trial model and evaluates the output against Section 7.
- **Not for Automation**: This is not an automated API test suite runner.
- **No Blocking Power**: Performance on these cases cannot be used to instantly grant a model autonomous merge authority or CI gate control.

## 9. Relationship to Existing Documents

- **Reviewer Integration**: Defines *how* the Reviewer is integrated into the PR flow.
- **Reviewer Supplementation Advisory Trial**: Defines the rules and constraints of *how we trial* the Reviewer model.
- **This Document**: Provides the concrete *sample data (what to test)* for that trial.
- This document does not replace or override the existing Roster, Fit Matrix, Trial Plan, Landing, or Enforcement Stub documents.

## 10. Next Hand-Off

Actionable next steps following the creation of this pack:

- Developing a **manual shadow review runbook** (step-by-step human guide to running these prompts).
- Integrating the case execution into **Reviewer-Author checklist integration**.
- Conducting the **Safety Advisory Trial plan**.
*(Do not expand backward into wording churn on blocker-reference documents).*

---

### Appendix: Sample-Case Output Template Block

> *(For docs presentation only. Not an executable script or bot runner spec.)*

\`\`\`markdown
**[Trial Run Observation]**

- **Case ID**: `REV-CASE-X`
- **Model Tested**: `[Model Name]`
- **Verdict**: [Pass / Fail / Inconclusive]
- **Notes**: Model successfully identified missing log evidence but hallucinated a non-existent formatting rule. Re-prompting required. Hand-off accurately targeted the PR Author.
\`\`\`
