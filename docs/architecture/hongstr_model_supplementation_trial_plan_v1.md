# HONGSTR Model Supplementation Trial Plan v1

## 1. Document Purpose

- This is the **HONGSTR Model Supplementation Trial Plan v1**.
- The purpose of this document is to define a conservative, small-scale framework for trialing new models to address specific role capability gaps.
- **This is NOT a shopping list for models.**
- **This is NOT a runtime orchestration spec.** It does not wire new APIs into `tg_cp` immediately.
- **This is NOT an immediate deployment order.** It simply governs *how* a trial must be conducted when a gap is identified.

## 2. Trial Principles

All model supplementation trials must strictly adhere to the following principles:

- **Supplement only when role gap is explicit**: Do not add models for general enhancement; tie every trial to a documented role bottleneck.
- **No model-pool sprawl**: Trials must be discrete. If a model fails its trial, it is removed, not left idling in the roster.
- **Trial before adoption**: No model is permanently adopted without a documented trial period yielding positive results.
- **Reversible by default**: Any trial must be capable of being instantly turned off (kill switch) to fall back to the existing dual-model or human baseline.
- **Report-only / Proposal-only first**: Trial models must operate under strict Phase B (advisory) constraints.
- **No truth-source mutation**: Trial models cannot autonomously write to `data/state/*`.
- **No autonomous deployment**: Trial models cannot unilaterally merge code or pass hard go/no-go gates.
- **Evidence-backed keep/remove decision**: The final decision to adopt a supplemented model must be based on recorded trial outputs.

## 3. Why Supplementation is Needed

Based on the *Role × Model Fit Matrix v1*, our current dual-model configuration (`qwen2.5-coder:7b` / `qwen2.5:7b`) successfully bootstraps the semantic framework but cannot safely render all roles fully autonomous. Specific bottlenecks exist:

- **Reviewer / Evidence Officer**: The 7B models struggle with the deep, multi-hop reasoning required to reliably map complex code diffs to acceptance criteria and telemetry logs without risk of rubber-stamping.
- **Safety Gatekeeper**: The local models cannot be trusted with final authority on detecting subtle logic bypasses or security zero-days.
- **Director of Quant Research**: High-level synthesis of alpha decay, regime shifts, and complex market semantics exceeds the grasp of lightweight local models.

Other roles (e.g., Ops Observer, Implementation Engineer, Gov. Librarian) currently function adequately within their boundaries and do not urgently require supplementation.

## 4. Supplementation Priority

Trials should be prioritized by systemic risk and QA necessity, rather than raw coding capability:

1. **First Priority**: Reviewer / Governance / Safety oriented capabilities. (Blocking bad changes is more critical than generating code faster).
2. **Second Priority**: High-level Quant Reasoning / Research Judgment capabilities.
3. **Not a Priority**: Implementation / Coding. The existing `qwen2.5-coder:7b` is sufficient for current rigidly scoped tasks.

## 5. Candidate Capability Types

Trials should target specific capability profiles rather than relying on brand allegiance.

### A. Reviewer / Evidence / Boundary Judgment Oriented Model

- **Target Role**: Reviewer / Evidence Officer, Adoption Coordinator.
- **Why Current Models Fail**: Inability to hold large context windows (diffs + logs + ACs) while maintaining strict deductive logic without hallucination.
- **Trial Operating Mode**: `review-only` / `proposal-only`.
- **Full Operation Limiter**: Must prove it can catch subtle evidence mismatches over dozens of PRs before being trusted not to rubber-stamp.

### B. Conservative Governance / Safety Oriented Model

- **Target Role**: Safety Gatekeeper.
- **Why Current Models Fail**: Prone to confidently dismissing subtle security edge cases if prompted assertively.
- **Trial Operating Mode**: `advisory-only` (reading script stdouts alongside a human).
- **Full Operation Limiter**: Safety gates must inherently default to human review unless a model achieves mathematically proven runtime verification capabilities (currently beyond scope).

### C. Deep Reasoning / Research Synthesis Oriented Model

- **Target Role**: Director of Quant Research.
- **Why Current Models Fail**: Unable to synthesize complex financial time-series semantics or identify structural market regime shifts.
- **Trial Operating Mode**: `analysis-support-only`.
- **Full Operation Limiter**: Alpha generation and tracking conviction remain strictly human-led.

## 6. Trial Scope Limits

During a trial, the supplemented model is heavily restricted. The first batch of trials is bounded strictly to:

- **Reviewer / Evidence Officer**: Generating Evidence Sufficiency Memos.
- **Safety Gatekeeper**: Generating advisory notes based strictly on `guardrail_check.sh` output.
- **Director of Quant Research**: Providing analysis support summaries.

**STRICT PROHIBITIONS DURING TRIAL:**

- Cannot assume Chief Steward final routing/decision authority.
- Cannot interact with the runtime truth-source write path (`data/state/*`).
- Cannot establish or enforce new CI hard gates autonomously.
- Cannot act as the final deployment authority.

## 7. Trial Operating Modes

Supplemented models undergoing trials are locked into the following modes:

- **Proposal-only**: Generating draft PRs, checklists, or adoption hooks.
- **Review-only**: Generating PR critiques and AC verification memos.
- **Advisory-only**: Flagging potential safety issues for human review.
- **Analysis-support-only**: Summarizing research data without making execution decisions.

During the trial period, these models **shall not** be upgraded to autonomous blocking or runtime action. Every judgment must culminate in a memo, recommendation, note, or verdict draft requiring human/Chief Steward sign-off.

## 8. Trial Assessment Criteria

To transition from "trial" to "adopted," the supplemented model must be evaluated against:

1. **Instruction-following stability**: Does it adhere to strict formatting and constraint prompts without drift?
2. **Red-line compliance**: Does it ever recommend mutating `src/hongstr` directly when forbidden?
3. **Evidence sufficiency judgment quality**: Does it accurately catch missing logs or telemetry?
4. **Overreach / Hallucination rate**: Does it invent false ACs or imagine code changes?
5. **Escalation discipline**: Does it proactively hand off to a human when uncertain?
6. **Output format consistency**: Are its Memos consistently machine-and-human-readable?
7. **Burden reduction**: Does its inclusion actually reduce the mental load on existing Human/Steward roles?
8. **Governance ambiguity**: Does it introduce confusion regarding who holds the final authority?

## 9. Keep / Remove / Rollback Rules

The trial must yield a deterministic outcome based on the assessment criteria:

- **Keep**: The model significantly reduces human burden in bottleneck roles without violating red lines or producing high hallucination rates. It is formalized into the Roster.
- **Remove / Triage**: The model frequently hallucinates, rubber-stamps bad evidence, or introduces governance ambiguity. The trial is terminated, and the model is discarded.
- **Pause Trial**: Unexpected API costs, rate limits, or integration friction occurs. Fall back immediately to baseline.
- **Rollback Baseline**: If the trial yields no significant capability jump over the baseline `qwen2.5:7b` for the bottleneck roles, do not expand the model pool. Revert to the dual-local-model fallback.

## 10. Trial Output & Recording

While not a runtime implementation, future script integrations driving these trials must log the following for post-mortem assessment:

- `role_tested` (e.g., Reviewer)
- `model_tested` (e.g., Target Capability Model API)
- `task_category` (e.g., PR Evidence Check)
- `advisory_output_type` (e.g., Sufficiency Memo)
- `escalation_result` (e.g., Handed off to human due to ambiguity)
- `trial_verdict` (Pass / Fail / Inconclusive)
- `rationale_summary`

## 11. Relationship to Existing Documents

- **Agent Roster**: Defines the *personas* and their rules.
- **Role × Model Fit Matrix**: Identifies the *gaps* in our current roster capabilities.
- **Adoption-Facing Deployment Guidance**: Clarifies *who* can deploy *now*.
- **Reviewer Integration**: Defines *how* the Reviewer currently hooks into the PR flow.
- **This Document**: Mandates *how cautiously we test new brains* to fill the identified gaps. It acts as the governance layer for procurement/testing.

## 12. Next Hand-Off

With the Trial Plan established, actionable next steps include:

- Executing a **Reviewer supplementation advisory trial task** (shadow testing an external model on a closed PR).
- Executing a **Safety Gatekeeper advisory trial task**.
- Drafting concrete **lightweight enforcement guidance** (the actual read-only scripts that would invoke these trial models).
*(Do not expand backward into wording churn on blocker-reference documents).*
