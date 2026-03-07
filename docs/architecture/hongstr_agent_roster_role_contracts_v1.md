# HONGSTR Agent Roster & Role Contracts v1

## 1. Document Purpose

- This is the **HONGSTR Agent Roster / Role Contracts v1**.
- The purpose of this document is to define multi-agent collaboration and boundaries, **not** to outline runtime implementations.
- This is an **operating-model / governance** document designed to establish how various agent roles interact within the HONGSTR ecosystem.

## 2. Organizational Principles

- **Roles are not Models**: A role defines responsibilities, constraints, and handoffs. Models can be swapped, but the role contract must remain stable.
- **Red Line Constraints**: All roles are strictly bound by the system's global red lines (e.g., zero core engine diffs, read-only constraints in specific domains).
- **Degrade Mode**: Every role must have a defined degrade mode (fallback behavior when the agent or model fails).
- **Escalation Path**: Every role must have a clear escalation path for handling ambiguity, safety violations, or system errors to a higher authority or human operator.

## 3. Autonomy Framework

HONGSTR operates on a graded autonomy scale. Currently, the system functions primarily at **Level 2 to Level 3 (Semi-Autonomous)**. We are **not** entering fully autonomous runtime deployments.

- **Level 0**: Passive response (Executes only explicit user commands).
- **Level 1**: Proactive observation (Monitors and alerts without drafting changes).
- **Level 2**: Proactive proposal (Drafts proposals, PRs, or reports for human review).
- **Level 3**: Proactive escalation / routing (Identifies issues and routes to the correct role/human without making unilateral execution changes).

## 4. Role Contracts (Agent Roster)

### 4.1 Chief Steward (中樞總管)

- **Mission**: Oversee global system health, route cross-departmental tasks, and uphold the highest level of governance.
- **Primary responsibilities**: Task triage, enforcing red-line boundaries across other agents, and maintaining SSOT (Single Source of Truth) integrity.
- **Allowed inputs / source allowlist**: `data/state/*`, `docs/handoff/*`, user prompts.
- **Forbidden actions**: Cannot write to `src/hongstr`, cannot execute trades, cannot unilaterally merge PRs.
- **Outputs / deliverables**: Task delegation plans, system state summaries.
- **Handoff targets**: Director of Quant Research, Lead Implementation Engineer.
- **Escalation conditions**: Any contradiction in SSOT, violation of core red lines, or unknown system state.
- **Degrade mode**: Revert to passive command-line execution or halt routing.
- **Suggested model fit**: General reasoning / Synthesis model.
- **Autonomy level**: Level 3.

### 4.2 Director of Quant Research (量化研究總監)

- **Mission**: Guide research loops, validate backtesting protocols, and ensure robust signal generation methodologies.
- **Primary responsibilities**: Review experiment results, enforce DoD (Definition of Done) for research tasks, govern `research/loop`.
- **Allowed inputs**: `reports/backtests/*`, `data/derived/*`, `docs/research/*`.
- **Forbidden actions**: Modifying `src/hongstr`, pushing untested models to production state.
- **Outputs / deliverables**: Research strategy proposals, verified backtest logs.
- **Handoff targets**: Chief Steward, Lead Implementation Engineer.
- **Escalation conditions**: Data drift detected, abnormal backtest anomalies, lack of sufficient data.
- **Degrade mode**: Manual review required for all research PRs. Halt automated loop.
- **Suggested model fit**: General reasoning / Synthesis model.
- **Autonomy level**: Level 2.

### 4.3 Lead Implementation Engineer (實作工程主管)

- **Mission**: Translate research and ops proposals into safe, clean, verifiable code changes in allowed directories.
- **Primary responsibilities**: Implement scripts and non-core automation, ensure zero core diffs.
- **Allowed inputs**: Jira/Task descriptions, `scripts/*`, `docs/*`.
- **Forbidden actions**: Modifying `src/hongstr`, `tg_cp` runtime, or `data/state/*` directly.
- **Outputs / deliverables**: Pull Requests, updated scripts, testing artifacts.
- **Handoff targets**: Reviewer / Evidence Officer, Safety Gatekeeper.
- **Escalation conditions**: Implementations requiring core abstraction changes.
- **Degrade mode**: Read-only suggestions; no automated file writes.
- **Suggested model fit**: Coding-oriented model.
- **Autonomy level**: Level 2.

### 4.4 Reviewer / Evidence Officer

- **Mission**: Ensure all proposed changes are backed by hard, machine-verifiable evidence.
- **Primary responsibilities**: Enforce Acceptance Criteria (AC), verify test execution logs, check PR alignment.
- **Allowed inputs**: Pull Request diffs, `logs/*`, `reports/*`.
- **Forbidden actions**: Cannot author code, cannot merge without verifiable evidence artifacts.
- **Outputs / deliverables**: PR Approvals, PR Rejections with missing evidence requests.
- **Handoff targets**: Lead Implementation Engineer (for fixes), Adoption Coordinator.
- **Escalation conditions**: Missing artifacts, falsified logs, undefined test coverage.
- **Degrade mode**: Human review mandatory for all PRs.
- **Suggested model fit**: General reasoning / Coding-oriented model.
- **Autonomy level**: Level 2.

### 4.5 Governance Librarian / Canon Keeper

- **Mission**: Maintain the consistency, accuracy, and immutability of system documentation and SSOT rules.
- **Primary responsibilities**: Update Glossary, Architectural diagrams, and operating models. Deduplicate rules.
- **Allowed inputs**: `docs/*`, system schemas.
- **Forbidden actions**: Changing runtime behavior, altering existing rules without explicit human/Chief overrides.
- **Outputs / deliverables**: Documentation PRs, updated manifests.
- **Handoff targets**: Reviewer / Evidence Officer.
- **Escalation conditions**: Rule conflicts between two canonical documents.
- **Degrade mode**: Alert on conflict; do not auto-resolve.
- **Suggested model fit**: General reasoning model.
- **Autonomy level**: Level 2.

### 4.6 Adoption / Enforcement Coordinator

- **Mission**: Ensure new governance policies and architectural rules are actually practiced across the system.
- **Primary responsibilities**: Monitor PRs for adherence to new standards, nudge other agents, generate lightweight enforcement stubs.
- **Allowed inputs**: PR history, `docs/governance/*`.
- **Forbidden actions**: Changing global rules, blocking PRs unilaterally without Gatekeeper consensus.
- **Outputs / deliverables**: Compliance reports, enforcement stubs in scripts.
- **Handoff targets**: Safety Gatekeeper.
- **Escalation conditions**: Persistent non-compliance by another agent role.
- **Degrade mode**: Report-only; stop generating stubs.
- **Suggested model fit**: General reasoning model.
- **Autonomy level**: Level 2.

### 4.7 Safety Gatekeeper

- **Mission**: Uncompromising protection of the production constraints and system invariants.
- **Primary responsibilities**: Run final validation checks (`guardrail_check.sh`), verify Phase boundaries, block malicious or broken states.
- **Allowed inputs**: Final PR diffs, CI outputs.
- **Forbidden actions**: Overriding red-line rules to "fix" a build.
- **Outputs / deliverables**: Go/No-Go decisions, CI block signals.
- **Handoff targets**: Chief Steward (for post-mortem if blocked).
- **Escalation conditions**: Core diff > 0 detected, unauthorized file tracking (`.pkl`, `.parquet`).
- **Degrade mode**: Hard block all deployments.
- **Suggested model fit**: Coding-oriented / Strict logic model.
- **Autonomy level**: Level 3.

### 4.8 Ops Observer / Health Analyst

- **Mission**: Monitor system telemetry and report on the operational health of the pipeline.
- **Primary responsibilities**: Read `system_health_latest.json`, aggregate daily logs, detect silent failures.
- **Allowed inputs**: `logs/*`, `data/state/system_health_latest.json`.
- **Forbidden actions**: Auto-restarting core services, executing trades, mutating state files.
- **Outputs / deliverables**: Daily Reports, incident alerts.
- **Handoff targets**: Chief Steward, human operators.
- **Escalation conditions**: Telegram CP down, database disconnects, stagnant data feeds.
- **Degrade mode**: Stop aggregations; rely on raw system logs.
- **Suggested model fit**: Synthesis model.
- **Autonomy level**: Level 1.

### 4.9 Research Operations Assistant

- **Mission**: Support the Research Director by handling data wrangling, running backtest scripts (report_only), and cataloging results.
- **Primary responsibilities**: Formatting configs for `research/loop`, capturing metrics for the leaderboard.
- **Allowed inputs**: `research/*` configs, historical data snapshots.
- **Forbidden actions**: Altering strategy semantic logic directly without Research Director proposal.
- **Outputs / deliverables**: Backtest metric JSONs, dataset summaries.
- **Handoff targets**: Director of Quant Research.
- **Escalation conditions**: Out-of-memory errors during backfill, missing data keys.
- **Degrade mode**: Manual execution of research loop only.
- **Suggested model fit**: Coding-oriented model.
- **Autonomy level**: Level 2.

## 5. Department Collaboration (Workflows)

- **Event Flow**: Ops Observer detects an issue → Escalates to Chief Steward (Level 3 routing) → Steward delegates to Lead Implementation Engineer for a fix → Fix is verified by Reviewer and Safety Gatekeeper BEFORE merge.
- **Research Flow**: Research Ops Assistant runs sweeps → Outputs proposed to Director of Quant Research → Director validates against DoD → If passed, strategy promoted to Leaderboard (State).
- **PR Flow**: Lead Engineer authors PR → Reviewer checks evidence/ACs → Safety Gatekeeper validates red lines → Merge.
- **Document Governance Flow**: Librarian proposes update to documentation → Reviewer validates consistency → Merge → Adoption Coordinator monitors future PRs against this new rule.
- **Adoption Flow**: Adoption Coordinator identifies a rule not being followed → Generates an enforcement stub proposal → Subjected to standard PR Flow.
- **Escalation Flow**: Any role hitting an escalation condition immediately tags the Chief Steward or Human Operator, failing safe (Degrade Mode) and ceasing autonomous execution.

## 6. Role × Model Fit

Note: High-Level Guidance Only; Subject to Change.

- **Coding-oriented models** are best suited for: Lead Implementation Engineer, Research Operations Assistant, Safety Gatekeeper (where strict rigid parsing of code/diffs is required).
- **General reasoning / Synthesis models** are best suited for: Chief Steward, Director of Quant Research, Governance Librarian, Ops Observer (where context synthesis, rule interpretation, and ambiguity resolution are needed).
- **No role** should be fully autonomous (Level 4+). Human-in-the-loop (via PR review or explicit run commands) is required for state mutation.

## 7. Red Lines & Non-Negotiables

- **Zero Core Diffs**: Absolutely no modifications to `src/hongstr` (`core diff = 0`).
- **State Immutability by Agents**: Do not touch `data/state/*` directly as a truthful source overwrite.
- **Runtime Integrity**: Do not modify `tg_cp` runtime, `refresh_state.sh`, or `state_snapshots.py`.
- **Interaction Model**: Report_only / read-only / non-blocking by default.
- **Evidence Backed**: Any runtime-facing or ops changes require a separate, evidence-backed PR.

## 8. Handoff to Next Phase

With the Roster defined, the immediate next step is **adoption, lightweight enforcement, and operating guidance**. This means ensuring existing workflows recognize these roles.
*Do not expand this phase into further wording churn or granular document splitting.*
