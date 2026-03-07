# HONGSTR Manual Shadow Review Runbook v1

## 1. Document Purpose

- This is the **HONGSTR Manual Shadow Review Runbook v1**.
- The purpose of this document is to provide a step-by-step human guide for executing a shadow review using a supplementary model.
- **This is NOT an automated reviewer bot specification.**
- **This is NOT a formal reviewer runtime adoption spec.**
- **This is NOT a CI gate configuration document.** It defines a purely manual, advisory-only trial operation.

## 2. Runbook Principles

All trial runs executed under this manual runbook must strictly adhere to the following principles:

- **Manual First**: A human must aggregate the inputs, query the model, and record the outputs. No automated PR webhooks.
- **Low-Risk First**: Run only against clearly defined, low-risk docs/governance/evidence cases from the Case Pack.
- **Advisory-Only / Non-Blocking**: The supplementary model's evaluation has zero blocking power on any actual PR or branch.
- **Reproducible & Comparable**: The prompt format and inputs must be consistent so different models can be apples-to-apples compared.
- **Reversible**: Since no system integration exists, stopping the trial simply means human operators stop running the queries.
- **No Truth-Source Mutation**: The trial does not write to `src/hongstr`, `data/state/*`, or `tg_cp`.
- **Human Reviewer Remains Final Authority**: The Chief Steward or designated Human Reviewer is the ultimate judge of both the PR and the Trial Model's utility.

## 3. Pre-Requisites

Before initiating a trial run, ensure the following conditions are met:

- **Case Selection**: You have selected a specific scenario from the `HONGSTR Reviewer Sample-Case Pack v1` (e.g., `REV-CASE-A1`).
- **Trial Definition**: You are operating under the rules defined in `HONGSTR Reviewer Supplementation Advisory Trial v1`.
- **Reviewer Presence**: A Human Reviewer / Chief Steward is available to perform the post-run evaluation.
- **Strict Boundary Acknowledgment**: You acknowledge that the supplementary model must not be allowed to form a binding `merge`, `reject`, `deploy`, or `block` decision.

## 4. Case Selection Step

1. Open the `HONGSTR Reviewer Sample-Case Pack v1`.
2. Select 1 to 3 low-risk cases (e.g., Docs, Governance, Adoption, Evidence Sufficiency).
3. Do **NOT** select complex core logic changes (`src/hongstr`) or truth-source mutations (`data/state/*`).
4. Note the Case ID, Category, Expected Task, and Expected Output for comparison later.

## 5. Input Preparation Step

The Human Operator must manually assemble the prompt context. This ensures consistency and prevents the model from searching externally and hallucinating context.

- **System Prompt**: Set the persona to "HONGSTR Supplementary Reviewer Agent" operating under the constraints of the Roster.
- **Case Background**: Provide the brief context of the PR/Action.
- **The Diff**: Copy-paste the exact code/docs diff.
- **The Evidence**: Copy-paste any attached logs (or explicitly state "No logs provided").
- **Acceptance Criteria (AC)**: Provide the specific rules the PR is supposed to satisfy.
- **Instruction**: Ask the model to generate the specific Output Type (e.g., Evidence Sufficiency Memo) based *only* on the provided inputs.

## 6. Reviewer Execution Step

1. Submit the prepared input to the target Supplementary Model (e.g., via a Chat UI or basic API script).
2. The model generates its response.
3. Ensure the model produced the requested format (e.g., a structured Draft Memo, not a rambling paragraph).
4. Do not engage in multi-turn debate if the model fails. The goal is to evaluate its zero-shot or one-shot reliability on a standard context block.

## 7. Human Review & Comparison Step

The Human Reviewer or Chief Steward evaluates the model output against the Case Pack's "Expected Behavior":

- **Helpfulness**: Did reading this Memo save the human time? Did it catch a missing log the human might have missed?
- **Overreach Detection**: Did the model hallucinate a new governance rule? Did it suggest rewriting `src/hongstr`?
- **Escalation Check**: Did the model correctly identify its limits and defer the final verdict to the Human Reviewer?
- **Verdict Alignment**: Does the model's conclusion (e.g., "Insufficient Evidence") match the Case Pack's orientation?

## 8. Trial Logging & Assessment

Record the outcome of the run. A minimum robust log should include:

- `Run_ID`: (e.g., `RUN-20260307-001`)
- `Case_ID`: The specific sample case used.
- `Supplementary_Model_Class`: The brand/size of the model tested.
- `Output_Type`: Did it output a Memo, Note, Notice?
- `Helpfulness_Assessment`: (1-5 scale or High/Med/Low).
- `Overreach_Observed`: Yes/No (If Yes, detail what was hallucinated).
- `Escalation_Discipline_Observed`: Yes/No.
- `Matched_Expected_Task`: Yes/No.
- `Trial_Verdict`: PASS, FAIL, or INCONCLUSIVE for this specific run.
- `Notes_Rationale`: Brief human commentary.

## 9. Handling the Results

- **PASS**: The model successfully completes several runs across different categories without overreach. It becomes a strong candidate for wider advisory use or lighter-weight localized script integration.
- **FAIL**: The model repeatedly hallucinates, rubber-stamps bad evidence, or assumes merge authority. Stop using this model class immediately.
- **INCONCLUSIVE**: The model performs well on wording checks but fails on evidence matching. Tighten the trial scope to only the successful categories and run more cases.
- *Reminder: These outcomes do not alter formal policy or deploy bots; they merely inform human architectural choices.*

## 10. Common Failure Modes to Watch For

When conducting standard reviews, humans must watch for these frequent LLM pitfalls:

1. **False Confidence**: Asserting that evidence is completely sufficient when critical logs are missing.
2. **Runtime Leaks**: Over-analyzing a low-risk docs PR and suggesting complex runtime architectural changes.
3. **Semantic Hallucination**: Misinterpreting source-role ambiguity or alias churn as acceptable variations.
4. **Escalation Failure**: Being completely unwilling to say "I don't know, this needs Chief Steward review", assuming it must render a definitive binary Pass/Fail verdict.
5. **Format Instability**: Producing unreadable output that ignores the requested Memo structure.

## 11. Relationship to Existing Documents

- **Reviewer Sample-Case Pack**: Provides the *content* (the cases) executed in this runbook.
- **Reviewer Supplementation Advisory Trial**: Provides the *rules and boundaries* for the trial.
- **Reviewer Integration**: Defines the *output artifacts* (Memos, Notes) the model is supposed to generate.
- **Model Supplementation Trial Plan**: Provides the overarching governance for testing any new capabilities.
- **This Document**: Simply tells the human operator *how to manually turn the crank* to execute the test.

## 12. Next Hand-Off

Actionable next steps following manual trial execution:

- Integrating successful prompt layouts into the **Reviewer-Author checklist**.
- Developing the **Safety Gatekeeper Advisory Trial Plan**.
- Drafting concrete **lightweight enforcement guidance** for successful models.
*(Do not expand backward into wording churn on blocker-reference documents).*

---

### Appendix: Minimal Manual Run Log Template

> *(For documentation purposes only. Use this format when recording runs in an issue or PR comment.)*

\`\`\`markdown
**[Manual Shadow Review Log]**

- **Run ID**: RUN-[Date]-[Index]
- **Case ID**: `[e.g., REV-CASE-A1]`
- **Tested Model**: `[Model Class]`
- **Helpfulness**: [High/Med/Low]
- **Overreach Observed**: [Yes/No] (Details if Yes)
- **Task Alignment**: [Matched / Hallucinated / Failed]
- **Run Verdict**: [PASS / FAIL / INCONCLUSIVE]
- **Human Notes**: Model properly caught the missing `guardrail_check.sh` output but used overly demanding tone. Content was accurate.
\`\`\`
