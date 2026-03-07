# HONGSTR Role × Model Fit Matrix v1

## 1. Document Purpose

- This is the **HONGSTR Role × Model Fit Matrix v1**.
- The purpose of this document is to catalog the suitability of our current active models against our defined agent roles. It serves as a tool for governance, task dispatch delegation, and future model procurement/supplementation decisions.
- **This is NOT a runtime dispatcher.** It does not govern the immediate execution pipeline (`tg_cp`), rather it dictates operating model guidelines.

## 2. Model Scope

The current local on-premise model pool consists primarily of:

- `qwen2.5-coder:7b-instruct`: Primary coding, structured parsing, and deterministic task-oriented model.
- `qwen2.5:7b-instruct`: General reasoning, text summarization, and coordination-oriented model.
- `nomic-embed-text:latest`: **Embedding-only model**. Used only for RAG/vector operations. Not eligible as a primary agent brain.

*Note*: External high-capability models (e.g., GPT-4 class, Claude Opus/Sonnet, Codex) are designated strictly as **reference / escalation targets** and are not subject to local, always-on, autonomous SLA commitments.

## 3. Role × Model Fit Matrix

### 3.1 Chief Steward (中樞總管)

- **Primary fit model**: `qwen2.5:7b-instruct`
- **Secondary / fallback model**: External High-Capability Model (via Human Escalation)
- **Suitability rating**: Moderate
- **Recommended autonomy level**: Level 3 (Routing / Proposal)
- **Operation type**: proposal-only / routing-only
- **Key risks**: May hallucinate complex multi-step routing logic or fail to identify deep SSOT contradictions.
- **Why this fit exists**: Role requires general synthesis of system health over rigid code generation.
- **Future model supplementation**: Yes, strong candidate for a broader context-window reasoning model.

### 3.2 Director of Quant Research (量化研究總監)

- **Primary fit model**: `qwen2.5:7b-instruct`
- **Secondary / fallback model**: Human / External High-Capability Model
- **Suitability rating**: Weak to Moderate
- **Recommended autonomy level**: Level 2
- **Operation type**: review-only / proposal-only
- **Key risks**: The 7b model currently lacks the deep domain expertise required to validate complex alpha signals or spot subtle over-fitting without heavy human-in-the-loop validation.
- **Why this fit exists**: Best currently available for strategy synthesis.
- **Future model supplementation**: Highly Recommended (Domain-specific quant reasoning model).

### 3.3 Lead Implementation Engineer (實作工程主管)

- **Primary fit model**: `qwen2.5-coder:7b-instruct`
- **Secondary / fallback model**: None (Fallback to Human Engineer)
- **Suitability rating**: Strong
- **Recommended autonomy level**: Level 2
- **Operation type**: stub-only / proposal-only
- **Key risks**: Could produce scripts that subtly violate red lines if prompt engineering fails.
- **Why this fit exists**: Excellent at translating defined tasks into distinct scripts or markdown docs.
- **Future model supplementation**: Not immediately urgent, current coder performs adequately within strict boundaries.

### 3.4 Reviewer / Evidence Officer

- **Primary fit model**: `qwen2.5-coder:7b-instruct` (for code/log diffs) & `qwen2.5:7b-instruct` (for AC alignment)
- **Secondary / fallback model**: Human Reviewer
- **Suitability rating**: Weak
- **Recommended autonomy level**: Level 2
- **Operation type**: review-only
- **Key risks**: High risk of rubber-stamping bad evidence or missing edge-case verification gaps. Limited ability to do deep forensic log analysis.
- **Why this fit exists**: Assigned by default to standard code-diff tracking, but struggles with large evidence files.
- **Future model supplementation**: **Critical Bottleneck**. Urgently needs a higher-tier reasoning model for rigorous QA validation.

### 3.5 Governance Librarian / Canon Keeper

- **Primary fit model**: `qwen2.5:7b-instruct`
- **Secondary / fallback model**: `qwen2.5-coder:7b-instruct`
- **Suitability rating**: Strong
- **Recommended autonomy level**: Level 2
- **Operation type**: proposal-only
- **Key risks**: Might inadvertently introduce conflicting governance phrases if not properly grounded by RAG.
- **Why this fit exists**: Good at synthesizing documentation and tracking definitions.
- **Future model supplementation**: Low priority.

### 3.6 Adoption / Enforcement Coordinator

- **Primary fit model**: `qwen2.5:7b-instruct`
- **Secondary / fallback model**: `qwen2.5-coder:7b-instruct` (for enforcement script generation)
- **Suitability rating**: Moderate
- **Recommended autonomy level**: Level 2
- **Operation type**: proposal-only / stub-only
- **Key risks**: High false-positive rate on compliance violations.
- **Why this fit exists**: Synthesizes PR history against governance rules.
- **Future model supplementation**: Moderate priority.

### 3.7 Safety Gatekeeper

- **Primary fit model**: `qwen2.5-coder:7b-instruct`
- **Secondary / fallback model**: Hard fail to Human
- **Suitability rating**: Weak to Moderate
- **Recommended autonomy level**: Level 3
- **Operation type**: can-operate (Blocking only)
- **Key risks**: May fail to identify a zero-day logic red-line bypass. Gatekeeper logic must rely primarily on deterministic scripts (`guardrail_check.sh`), with LLM purely acting as a reader of the script's stdout.
- **Why this fit exists**: Needs strict JSON/log output parsing.
- **Future model supplementation**: **Critical Bottleneck**. Safety demands high reliability.

### 3.8 Ops Observer / Health Analyst

- **Primary fit model**: `qwen2.5:7b-instruct`
- **Secondary / fallback model**: Simple rule-based alerts
- **Suitability rating**: Strong
- **Recommended autonomy level**: Level 1
- **Operation type**: can-operate (Read-only alerts)
- **Key risks**: Alert fatigue from overly verbose summaries.
- **Why this fit exists**: Excels at summarizing JSON health states into human-readable daily reports.
- **Future model supplementation**: Low priority.

### 3.9 Research Operations Assistant

- **Primary fit model**: `qwen2.5-coder:7b-instruct`
- **Secondary / fallback model**: None
- **Suitability rating**: Strong
- **Recommended autonomy level**: Level 2
- **Operation type**: stub-only
- **Key risks**: Incorrectly parsing JSON configs leading to flawed backtests.
- **Why this fit exists**: Rigid JSON manipulation and data plumbing.
- **Future model supplementation**: Low priority.

## 4. Overall Assessment of Core Models

- **`qwen2.5-coder:7b-instruct`**: Excels heavily in coding, implementation stubs, structured document work, and rigid format parsing.
- **`qwen2.5:7b-instruct`**: Geared toward semantic coordination, natural language summarization, generic reasoning, and human-facing report generation.
- **Conclusion**: The current dual-model setup is sufficient to bootstrap the multi-agent operating model framework, but **we cannot assume all roles are fully autonomous.** Certain roles can only operate safely as semi-autonomous (proposal-only) actors due to the intrinsic reasoning limits of 7B-class models.

## 5. Identification of Bottleneck Roles

The following roles represent the most severe risks under the current 7B model limitation and act as system bottlenecks:

1. **Reviewer / Evidence Officer**: Verification requires deep context mapping between intent, code change, and output trace. The 7B models frequently struggle with this multi-hop reasoning, risking rubber-stamping.
   - *Mitigation/Degrade*: Human mandatory review on all high-impact evidence PRs.
2. **Safety Gatekeeper**: The final line of defense. The LLM cannot be trusted to holistically assess security.
   - *Mitigation/Degrade*: The LLM should only read the deterministic output of `guardrail_check.sh` and not evaluate the raw diffs itself for safety.
3. **Director of Quant Research (High-Level Check)**: Assessing alpha decay, regime shifts, and complex quantitative concepts exceeds the general reasoning capability of the locally hosted 7B model.
   - *Mitigation/Degrade*: Operates purely as a pipeline automation supervisor rather than an alpha-generator.

**If future models are supplemented, they must prioritize QA validation, safety auditing, and deep logic verification over generic coding capabilities.** We are not directly specifying a brand, but rather the *capability gap* (e.g., highly reliable evaluation/review models).

## 6. Model Supplementation Principle (補模原則)

- **No Unjustified Expansion**: Model pool bloat is forbidden. Do not add models aimlessly.
- **Targeted Gap Filling**: Only procure or deploy a new model when a specific role (e.g., Reviewer) hits a proven, documented capability gap in an active task.
- **Priority Queue**: Address `reviewer / governance / safety` capability gaps before enhancing `generation / coding` capabilities.
- **Trial Runs**: Any newly introduced model must undergo an observation trial period before it can officially retire or replace an existing primary model on the roster.

## 7. Task Dispatch Principle (派工原則)

- **To `qwen2.5-coder:7b-instruct`**: Route PR creation, script stubbing, strict JSON manipulation, and rigid formatting tasks.
- **To `qwen2.5:7b-instruct`**: Route daily reporting, event summarization, documentation consistency checks, and triage analysis.
- **Final Verdicts**: **Never** rely solely on existing local AI models for final, irreversible production verdicts.
- **High-Risk Escalation**: Any task involving core logic restructuring, anomalous state recovery, or direct runtime interaction must be escalated to an external high-capability model or human override.

## 8. Next Steps

With the Agent Roster and this Fit Matrix established, the next logical step must be:

- **Adoption-facing role deployment guidance**: Creating a lightweight, non-blocking rollout for specific low-risk roles. *See [HONGSTR Adoption-Facing Role Deployment Guidance v1](./hongstr_adoption_facing_role_deployment_guidance_v1.md)*.
- **Targeted Model Supplementation Trial Plan**: A controlled proposal evaluating a specific model upgrade for defined bottleneck roles. *See [HONGSTR Model Supplementation Trial Plan v1](./hongstr_model_supplementation_trial_plan_v1.md)*.
*(Do not expand backward into wording churn on old blockers).*
