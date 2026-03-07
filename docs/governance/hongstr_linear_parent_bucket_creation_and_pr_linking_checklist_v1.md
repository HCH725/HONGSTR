# HONGSTR Linear Parent Bucket Creation and PR Linking Checklist v1

## 1. Document Purpose

- This is a **Linear Parent Bucket Creation and PR Linking Checklist**.
- The unique purpose of this guide is to provide a copy-pasteable execution list for reverting the recent batch of orphan PRs (#281–#292) back into HONGSTR’s strict **Linear-first governance** flow.
- **This is NOT a new feature specification or strategy document.**
- **This is NOT a runtime rollout definition.**

## 2. Linear Parent Items to Create (Templates)

*Human Action: Create the following 3 parent items in Linear.*

### A. Parent 1

- **Title**: `Phase B1 Local-Agent Operating Model Definition`
- **Classification**: `MAINLINE`
- **Scope**: Absorbs established formal governance skeleton documents for the multi-agent operating model. This includes role contracts, role × model fit, adoption guidance, reviewer integration, and model supplementation governance baseline.
- **Recommended PR attachments**: `#281`, `#282`, `#283`, `#284`, `#285`
- **Recommended closure meaning**: GitHub merge means the governance baseline is formally documented. It does **not** equal full runtime adoption of all roles.

### B. Parent 2

- **Title**: `Reviewer Supplementation Advisory Trial Planning`
- **Classification**: `CANDIDATE / REVIEW`
- **Scope**: Absorbs the candidate/trial-layer docs for the reviewer advisory trial. Includes reviewer supplementation trial plan, sample-case pack, and manual shadow review runbook.
- **Recommended PR attachments**: `#286`, `#287`, `#289`
- **Recommended closure meaning**: **GitHub merge != reviewer trial completed**. Linear outcome should be mapped post-merge to `DONE (planning/docs ready only)`, `DEFERRED`, or `SUPERSEDED` based on subsequent human execution of the trial.

### C. Parent 3

- **Title**: `LLM Multi-Agent Inspiration & Backlog Catalog`
- **Classification**: `SANDBOX`
- **Scope**: Absorbs external multi-agent / MCP / RAG / planner-executor inspiration into an isolated backlog mapping. Does not constitute adoption authorization.
- **Recommended PR attachments**: `#292`
- **Recommended closure meaning**: `SANDBOX ONLY` or `SUPERSEDED`.

## 3. PR-to-Parent Mapping Table

| PR #  | Topic                                    | Proposed Parent Bucket                               | Proposed Classification | Recommended Linear Outcome                                | Why                                                                                                    |
|-------|------------------------------------------|------------------------------------------------------|-------------------------|-----------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| #281  | Agent Roster / Role Contracts            | Phase B1 Local-Agent Operating Model Definition      | MAINLINE                | `MERGED`                                                  | Foundational mainline role definitions.                                                                |
| #282  | Role × Model Fit Matrix                  | Phase B1 Local-Agent Operating Model Definition      | MAINLINE                | `MERGED`                                                  | Core capacity definition complementing the roster.                                                     |
| #283  | Adoption Deployment Guidance             | Phase B1 Local-Agent Operating Model Definition      | MAINLINE                | `MERGED`                                                  | Establishes official phased deployment constraints.                                                    |
| #284  | Reviewer Role Integration                | Phase B1 Local-Agent Operating Model Definition      | MAINLINE                | `MERGED`                                                  | Formalizes Reviewer boundary rules.                                                                    |
| #285  | Model Supplementation Trial Plan         | Phase B1 Local-Agent Operating Model Definition      | MAINLINE                | `MERGED`                                                  | Global principles for running any model trial.                                                         |
| #286  | Reviewer Advisory Trial                  | Reviewer Supplementation Advisory Trial Planning     | CANDIDATE / REVIEW      | `DONE (planning/docs ready)`, `DEFERRED`, or `SUPERSEDED` | **GitHub merge != Linear trial completion**. Documenting the trial does not mean it was executed yet.  |
| #287  | Reviewer Sample-Case Pack                | Reviewer Supplementation Advisory Trial Planning     | CANDIDATE / REVIEW      | `DONE (planning/docs ready)`, `DEFERRED`, or `SUPERSEDED` | **GitHub merge != Linear trial completion**.                                                           |
| #289  | Manual Shadow Review Runbook             | Reviewer Supplementation Advisory Trial Planning     | CANDIDATE / REVIEW      | `DONE (planning/docs ready)`, `DEFERRED`, or `SUPERSEDED` | **GitHub merge != Linear trial completion**.                                                           |
| #292  | Inspiration Mapping / Role Backlog       | LLM Multi-Agent Inspiration & Backlog Catalog        | SANDBOX                 | `SANDBOX ONLY` or `SUPERSEDED`                            | Speculative archive.                                                                                   |

## 4. Crucial Closure Rules (Trial PRs)

For PRs `#286`, `#287`, and `#289`, you must explicitly recognize that merging the text into GitHub does **not** signify that the trial phase succeeded or concluded.
The Linear representation of these items must only be set to `DONE (planning/docs ready only)`, `DEFERRED`, or `SUPERSEDED`.
**GitHub merge != Linear trial completion.**

## 5. Human Execution Steps

To execute this backfill constraint safely, the Human Operator (Chief Steward) must perform the following:

1. **In Linear**: Create the 3 Parent Items exactly as structured in Section 2. Note their new IDs (e.g., `LIN-101`, `LIN-102`, `LIN-103`).
2. **In GitHub**: For PRs `#281` through `#292`, attach each back to its target Parent Bucket.
3. **In GitHub**: Edit the PR description or add a PR comment explicitly noting the generated Linear ID.
4. **In Linear/GitHub**: Decide on the formal closure outcome for each PR based on the mapping table (e.g., merging the mainline docs, setting trial docs to `DONE (planning ready)`).
5. **Hard Stop**: In this precise step, do not initiate or resume any new automated or agent-led implementations.

## 6. HARD STOP STATEMENT

**Under no circumstances should any new local-agent, reviewer, or multi-agent governance implementations or document themes be initiated until PRs #281 through #292 have successfully completed this Linear tracking backfill and closure alignment.**
