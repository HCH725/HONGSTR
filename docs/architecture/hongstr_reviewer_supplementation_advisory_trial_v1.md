# HONGSTR Reviewer Supplementation Advisory Trial v1

## 1. Document Purpose

- This is the **HONGSTR Reviewer Supplementation Advisory Trial v1**.
- The purpose of this document is to specifically outline how the **Reviewer / Evidence Officer** role will undergo a model supplementation trial.
- **This is NOT a formal adoption specification** for a new permanent runtime model.
- **This is NOT a final review authority spec.**
- **This is NOT a CI hard gate specification.** It defines an advisory, non-blocking trial only.

## 2. Why Trial the Reviewer Role First?

Based on the *Role × Model Fit Matrix v1* and the *Model Supplementation Trial Plan v1*, the Reviewer has been identified as a definitive operational bottleneck:

- **Capability Gap**: The existing dual-local-model setup (`qwen2.5-coder:7b` / `qwen2.5:7b`) lacks the deep, multi-hop contextual reasoning required to safely synthesize PR diffs, validation logs, and acceptance criteria without a high risk of rubber-stamping.
- **Risk Mitigation**: Trialing a supplementary model in an advisory-only Reviewer capacity carries lower systemic risk than directly trialing a Safety Gatekeeper (which governs absolute red lines).
- **Value Proposition**: The Reviewer role provides the clearest, most immediate signal for evaluating whether a new model can genuinely reduce human QA burden.

## 3. Trial Role Positioning

During this trial, the supplementary model must be strictly boxed into the following constraints:

- **Role Status**: The model acts solely as a **Supplementary Reviewer**.
- **Allowed Operating Modes**: `advisory-only` / `review-only` / `proposal-only`.
- **Prohibited Authority**:
  - The supplementary reviewer is **NOT** the final merge authority.
  - The supplementary reviewer is **NOT** the final safety gate.
  - The supplementary reviewer **MUST NOT** directly modify truth sources (`data/state/*`), execution runtimes (`tg_cp`), or deployment paths.

## 4. Authorized Trial Task Categories

The trial is authorized to test the model's performance on the following specific task types:

- Drafting **Evidence Sufficiency Memos** (validating log outputs against ACs).
- Drafting **Reviewer Notes** (general PR feedback).
- Providing **Reopen / Do-Not-Reopen Recommendations** (assessing if a previously failed PR now meets criteria).
- Performing preliminary semantic checks on **canonical wording, alias churn, or source-role ambiguity**.
- Conducting advisory reviews on **Governance PRs, Docs PRs, Role Contract updates, or Adoption Guidance updates**.

> **Explicitly Excluded Tasks:**
> The trial model MUST NOT be used to generate final verdicts on `src/hongstr` core modifications, `data/state/*` truth-source changes, or `tg_cp` runtime logic.

## 5. Strict Operating Constraints

To ensure safety and reversibility, the following constraints are non-negotiable during the trial:

- The supplementary model **shall not be the only reviewer**; human cross-reference is mandatory.
- The trial outputs **shall not form a hard block** in CI or any deployment pipeline.
- The model **cannot override** decisions made by a Human Reviewer, the Chief Steward, or a higher-tier external pathway.
- The model cannot autonomously execute `merge`, `reject`, or `deploy` actions.
- All trial outputs must be explicitly labeled as a **Memo, Recommendation, Note, or Draft Verdict**.

## 6. Trial Workflow Guidance

> *(This section defines the human-in-the-loop workflow; it does not mandate automated GitHub Actions at this stage. See [HONGSTR Manual Shadow Review Runbook v1](./hongstr_manual_shadow_review_runbook_v1.md) for step-by-step execution.)*

1. **Trigger**: A PR matching the authorized task categories (e.g., a documentation or governance update) is opened.
2. **Input Generation**: A human or a lightweight prep-script aggregates the PR description, code diff, and attached evidence logs.
3. **Execution**: The supplementary model is queried using the aggregated input, instructed to act under the *Reviewer Role Contract*.
4. **Output Generation**: The model produces a designated artifact (e.g., an Evidence Sufficiency Memo).
5. **Handoff & Verdict**: The output is attached to the PR as a comment. The **Human Reviewer or Chief Steward** reads the memo and makes the final determination to accept, reject, or ignore the model's advice.

## 7. Evaluation Criteria

To determine if the trial is successful, the supplementary model will be evaluated against the following metrics:

- **Evidence Judgment Quality**: Did it accurately identify missing or mismatched test evidence?
- **Reopen Recommendation Quality**: Was its logic sound when evaluating fixes against previous failures?
- **False Confidence / Overreach Rate**: Did it hallucinate ACs or make assertions beyond the provided diffs?
- **Escalation Discipline**: Did it correctly identify when a PR touched forbidden paths and flag it for human/Chief Steward review?
- **Output Structure Consistency**: Did it adhere to the requested Memo/Note formats?
- **Utility**: Did reading the model's output actually save time for the human reviewer or Chief Steward?
- **Governance Clarity**: Did its involvement clarify rather than confuse the enforcement of established rules?

## 8. Trial Outcome Classifications

Based on the evaluation criteria, the trial will conclude with one of the following decisions:

- **Keep for continued advisory use**: The model proves highly reliable and significantly reduces reviewer burden. It is formally integrated into the Roster as the primary advisory Reviewer.
- **Continue with tighter scope**: The model is useful but struggles with certain PR types (e.g., struggles with logs but excels at docs). The trial is narrowed.
- **Inconclusive / Need more cases**: The sample size is too small to make a definitive judgment.
- **Remove / Rollback**: The model hallucinates frequently, rubber-stamps bad evidence, or adds negative value. The model is discarded and we revert to the human-baseline/local-fallback.

> *(Note: If the trial does not yield a decisive improvement in the Reviewer bottleneck, the model will not be adopted.)*

## 9. Trial Recording Ledger (High-Level Schema)

While not an executable script, any trial runs should be manually or semi-automatically recorded with the following data points for governance review:

- `PR_Number_or_Test_Case`
- `Supplementary_Model_Class` (e.g., DeepSeek-R1-API, Claude-3.5-Sonnet)
- `Advisory_Output_Type` (e.g., Evidence Sufficiency Memo)
- `Escalation_Outcome` (e.g., Flagged Core Modification)
- `Human_Adoption_Verdict` (Accept / Reject / Inconclusive)
- `Usefulness_Summary` (e.g., "Caught a missing edge-case in AC2")
- `Overreach_Observed` (Yes/No)
- `Rationale_Summary`

## 10. Document Hierarchy & Relationship

- **Agent Roster**: Defines the Reviewer persona and its behavioral contract.
- **Role × Model Fit Matrix**: Identifies the Reviewer as a critical reasoning bottleneck.
- **Adoption Guidance**: Authorizes the Reviewer to operate only in proposal/advisory modes.
- **Reviewer Integration**: Defines the specific output formats (Memos, Notes) the Reviewer should produce in the PR lifecycle.
- **Model Supplementation Trial Plan**: Establishes the overarching conservative principles for adding *any* new model.
- **This Document**: Acts as the specific **execution blueprint for the Reviewer Trial**, adhering to all parent constraints.

## 11. Next Hand-Off

Following the establishment of this advisory trial plan, the immediate next steps are:

- Compiling a **Reviewer Case Set / Shadow Review Sample Pack** (e.g., running the target model against a set of historical closed/merged PRs to test judgment). *See [HONGSTR Reviewer Sample-Case Pack v1](./hongstr_reviewer_sample_case_pack_v1.md)*.
- Integrating the request for these advisory memos into the **Reviewer-Author PR Checklists**.

> *(Optional Parallel Track): Drafting the Safety Gatekeeper Advisory Trial Plan.*

---

### Appendix: Sample Advisory Output Format

> *(Docs-Only Example. Not a runtime executable template.)*

\`\`\`markdown
**[Supplementary Reviewer Memo: Advisory Only]**

- **Model Assessed**: `[Target Trial Model]`
- **Task**: Evidence Sufficiency Check (Docs PR)
- **Verdict Draft**: Sufficient.
- **Rationale**: The diff strictly modifies `.md` files in `docs/architecture/`. No core paths (`src/hongstr`) are touched. The wording aligns with the Agent Roster constraints.
- **Escalation**: None required for docs-only, handing off to Human Reviewer for final merge approval.
\`\`\`
