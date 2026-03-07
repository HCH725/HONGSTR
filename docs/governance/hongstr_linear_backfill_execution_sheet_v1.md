# HONGSTR Linear Backfill Execution Sheet v1

## 1. Document Purpose

- This is a **Linear backfill execution sheet**.
- Its strict purpose is to assist humans in importing the recently generated local-agent, reviewer, and operating-model orphan PRs back into the **Linear-first governance** tracking system.
- **This is NOT a functional specification.**
- **This is NOT a new feature rollout or runtime change.**

## 2. Recommended Linear Parent Buckets to Create

*Human Action: Create the following 3 parent items in Linear.*

### A. MAINLINE Parent

- **Title**: `Phase B1 Local-Agent Operating Model Definition`
- **Description**: Absorbs the formalized governance skeleton for the multi-agent operating model. This covers role definitions, role-to-model fit matrices, deployment guidance, reviewer integration rules, and overarching supplementation trial principles.
- **PRs to Attach**: `#281`, `#282`, `#283`, `#284`, `#285`
- **Closure Rule**: Merging these PRs simply means the *governance documents* are complete and baselined. It does **not** imply that all agents are formally adopted into runtime execution.

### B. CANDIDATE / REVIEW Parent

- **Title**: `Reviewer Supplementation Advisory Trial Planning`
- **Description**: Absorbs the candidate/trial-layer documentation for the reviewer advisory trial. This includes the trial definition, the sample-case pack, and the manual shadow review runbook.
- **PRs to Attach**: `#286`, `#287`, `#289`
- **Closure Rule**: Merging these PRs means the trial *plan* is formally staged on `main`. **Crucially: GitHub merge != Linear trial completion.** The Linear item should remain open and move through `DONE`, `DEFERRED`, or `SUPERSEDED` only based on actual post-merge trial outcomes.

### C. SANDBOX Parent

- **Title**: `LLM Multi-Agent Inspiration & Backlog Catalog`
- **Description**: Absorbs external multi-agent, MCP, RAG, and planner-executor inspirations as a backlog mapping document. Does not authorize any formal adoption or runtime execution.
- **PRs to Attach**: `#292`
- **Closure Rule**: `SANDBOX ONLY` or `SUPERSEDED`.

## 3. PR-to-Parent Mapping Table

| PR # | Topic | Proposed Parent Bucket | Classification | Recommended Linear Outcome | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **#281** | Agent Roster / Role Contracts | `Phase B1 Local-Agent Operating Model Definition` | MAINLINE | MERGED | Foundational Roster. |
| **#282** | Role × Model Fit Matrix | `Phase B1 Local-Agent Operating Model Definition` | MAINLINE | MERGED | Model capacity baseline. |
| **#283** | Adoption Deployment Guidance | `Phase B1 Local-Agent Operating Model Definition` | MAINLINE | MERGED | Deployment safety phases. |
| **#284** | Reviewer Role Integration | `Phase B1 Local-Agent Operating Model Definition` | MAINLINE | MERGED | Reviewer PR boundary rules. |
| **#285** | Model Supplementation Trial Plan | `Phase B1 Local-Agent Operating Model Definition` | MAINLINE | MERGED | Overarching trial rules. |
| **#286** | Reviewer Advisory Trial | `Reviewer Supplementation Advisory Trial Planning` | CANDIDATE / REVIEW | *(Depends on Trial Result)* | **GitHub merge != Linear trial completion.** |
| **#287** | Reviewer Sample-Case Pack | `Reviewer Supplementation Advisory Trial Planning` | CANDIDATE / REVIEW | *(Depends on Trial Result)* | **GitHub merge != Linear trial completion.** |
| **#289** | Manual Shadow Review Runbook | `Reviewer Supplementation Advisory Trial Planning` | CANDIDATE / REVIEW | *(Depends on Trial Result)* | **GitHub merge != Linear trial completion.** |
| **#292** | Inspiration Mapping / Backlog | `LLM Multi-Agent Inspiration & Backlog Catalog` | SANDBOX | SANDBOX ONLY | Archive-only backlog document. |

## 4. Manual Linear Backfill Steps

*Human Action: Execute the following sequence exactly.*

1. **Create Parent Items**: In Linear, manually create the 3 Parent tickets listed in Section 2. Note their Linear IDs (e.g., `LIN-101`, `LIN-102`, `LIN-103`).
2. **Attach PRs**: For each open PR in GitHub (#281-#292), edit the PR description or add a comment linking it to the newly created Linear ID.
3. **Execute Merge**: Review the PRs on GitHub and execute the merges to establish the new `main` branch SSOT.
4. **Determine Final Linear State**: Follow the Closure Rules defined above. Do not blindly mark the Trial items as `DONE` simply because the text was merged.
5. **Enforce Hard Stop**: Do not instruct local agents to resume new implementation work until Step 4 is complete.

## 5. HARD STOP DECLARATION

**Until PRs #281 through #292 complete their Linear tracking backfill and formal GitHub closure, DO NOT initiate new local-agent governance document creation, new role deployments, new safety trials, or any runtime integration work.** The system is currently in a forced pause for Linear-first reconciliation.
