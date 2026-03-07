# HONGSTR Adoption-Facing Role Deployment Guidance v1

## 1. Document Purpose

- This is the **HONGSTR Adoption-Facing Role Deployment Guidance v1**.
- The purpose of this document is to clarify *how* the defined multi-agent roles can begin operating safely in the current environment.
- **This is NOT a runtime orchestration spec or an enforcement engine.** It dictates the operational rollout phases, classifying which roles are ready to act, which roles must remain advisory, and which must be withheld from autonomous operation.

## 2. Deployment Principles

To ensure we adhere to HONGSTR's Stage 8 constraints, all role deployments must strictly follow these principles:

- **Read-Only First**: Initial deployments must not perform state mutations.
- **Proposal Before Action**: Agents must draft changes (e.g., in a PR or stub) rather than executing them directly against the SSOT.
- **Human Oversight on High-Risk Roles**: Critical gates and alpha validation must be human-reviewed.
- **No Runtime Truth-Source Mutation**: Agents run alongside the system (`tg_cp`), analyzing data, but do not autonomously interact with or bypass the execution environment.
- **No Autonomous Deployment**: All deployments must pass through standard evidence-backed PRs.

## 3. Role Groupings (Deployment Status)

### Group A: Can-Operate Now (Read-Only / Reporting)

These roles pose minimal risk to core logic and state mutability. They can be deployed immediately in a read-only or reporting capacity.

- **Ops Observer / Health Analyst**: Aggregates logs, checks freshness, and generates daily heartbeat summaries.
- **Governance Librarian / Canon Keeper**: Audits documentation consistency, cross-references definitions, and highlights canonical drift.
- **Research Operations Assistant**: Runs headless backtests (report-only mode), formats configurations, and catalogs results into the leaderboard.

### Group B: Proposal-Only / Review-Only / Stub-Only

These roles interact with core logic indirectly or perform complex semantic evaluations that our current 7B models cannot fully guarantee. They must operate in an advisory capacity.

- **Adoption / Enforcement Coordinator**: Can propose adoption hooks or compliance stubs via PR, but cannot autonomously halt or revert changes in CI.
- **Reviewer / Evidence Officer**: Can generate review memos, identify missing test evidence, and draft PR checklists, but **cannot provide final PR approval**.

### Group C: Not Yet Fully Operational (Human / Escalation Required)

These roles govern critical safety and ultimate business logic, exceeding the boundaries of current local model guarantees.

- **Safety Gatekeeper**: The local model cannot be trusted to definitively assess security or zero-day bypasses. It must rely strictly on deterministic script outputs (`guardrail_check.sh`), failing over to human assessment on any ambiguity.
- **Director of Quant Research**: Evaluating subtle statistical over-fitting, regime shifts, and complex market semantics must remain human-directed or escalated to a higher-capacity external model.
- **Chief Steward**: The Chief Steward can route tasks but cannot unilaterally act as the final arbiter on cross-departmental truth-source mutations.

## 4. Detailed Role Operating Modes

| Role | Status | Operating Mode | Allowed Tasks | Disallowed Tasks | Required Oversight | Current Suggested Fit | Escalation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Ops Observer** | Active | `can-operate` | Read logs, draft daily standard summaries. | Auto-restart services, execute trades, edit `tg_cp` runtime. | Low (Summaries only) | `qwen2.5` | Human Operator |
| **Gov. Librarian** | Active | `can-operate` | Deduplicate definitions, build cross-refs, parse markdown. | Change rules without PR, modify non-doc logic. | Low (PR review required) | `qwen2.5` | Chief Steward |
| **Research Ops** | Active | `can-operate` | Format JSON configs, trigger `report_only` backtests, summarize metrics. | Alter strategy logic, mutate `data/state`. | Medium | `coder` | Quant Director |
| **Enforcement Coordinator** | Staged | `proposal-only` | Draft lightweight validation scripts or checks. | Add CI hard gates autonomously. | High (PR review) | `qwen2.5` / `coder` | Gatekeeper |
| **Reviewer** | Staged | `review-only` | Parse ACs, match evidence to diffs, draft PR feedback. | Approve PRs, merge code. | High (Human co-review) | Both | Chief Steward |
| **Safety Gatekeeper** | Hold | `not-yet-deploy` | Read `stdout` of guardrail checks. | Evaluate code diffs for safety independently. | Mandatory Human | `coder` | Human Operator |
| **Quant Director** | Hold | `not-yet-deploy` | Propose strategy templates. | Final sign-off on tracking or live execution. | Mandatory Human | `qwen2.5` | External Model |
| **Chief Steward** | Hold | `not-yet-deploy` | Draft task dispatch plans. | Mutate SSOT, force overrides. | Mandatory Human | `qwen2.5` | Human Operator |

## 5. First-Batch Viable Workflows

The following workflows are explicitly cleared for immediate use under current constraints:

- **Ops Summary Generation**: Ops Observer parsing `system_health_latest.json` to generate the daily health report draft.
- **Doc Consistency Verification**: Governance Librarian scanning `docs/` to ensure new files link back to the Roster or Fit Matrix.
- **Research Artifact Cataloging**: Research Ops Assistant pushing raw test output into standard leaderboard JSON structures (must still be merged via PR).
- **PR Initial Screening**: Reviewer agent parsing a new PR description and generating a "Missing Evidence / AC Checklist" memo as a comment, but not blocking.

## 6. High-Risk Scenarios (Strictly Prohibited Autonomous Action)

The following must **never** be performed autonomously by the agent system at this stage:

- Direct modification of `src/hongstr` or `tg_cp` runtime code.
- Direct overwrite of Truth Sources (`data/state/*`).
- Final binary Go/No-Go decisions for production deployment without human approval.
- Final safety gate blocking based purely on non-deterministic LLM analysis instead of a hard script.
- Final quantitative reasoning and alpha selection without external or human review.

## 7. Phased Adoption Strategy

- **Phase B1 (Current)**: Read-only, reporting, and organizational tasks (`can-operate` for Group A).
- **Phase B2 (Current/Next)**: Proposal-only, review assistance, and adoption hook drafting (`proposal-only` for Group B).
- **Future Phase**: Minimal runtime-facing bridging. (This requires significant model capability improvements and separate evidence-backed governance PRs. Currently Out of Scope).

## 8. Document Hierarchy Relationship

- *Blocker-Reference Landing/Enforcement*: Governs the *rules* and code changes.
- *Agent Roster*: Defines the *job descriptions* and *responsibilities* of each system persona.
- *Role × Model Fit Matrix*: Assesses our *technical capacity* to fulfill those job descriptions using existing local models.
- **This Document (Deployment Guidance)**: Dictates the *operational timeline and access level* for putting those models into those roles. It does not replace any of the above.

## 9. Next Hand-Off

To progress the multi-agent system further within these safe boundaries, the next logical steps are:

- Lightweight enforcement guidance (e.g., scripting the Reviewer's PR checklist automation).
- Reviewer / Author adoption integration: *See [HONGSTR Reviewer Role Deployment Integration v1](./hongstr_reviewer_role_deployment_integration_v1.md)*.
- Evaluating future roles: *See [HONGSTR Inspiration Mapping / Role Backlog v1](./hongstr_inspiration_mapping_role_backlog_v1.md)*.
