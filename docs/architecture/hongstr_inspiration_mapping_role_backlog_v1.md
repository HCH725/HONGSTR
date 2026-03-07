# HONGSTR Inspiration Mapping / Role Backlog v1

## 1. Document Purpose

- This is the **HONGSTR Inspiration Mapping / Role Backlog v1**.
- The purpose of this document is to systematically filter and absorb external multi-agent, MCP, and LLM orchestration patterns into HONGSTR's governable architecture backlog.
- **This is NOT a feature specification or execution plan.**
- **This is NOT a runtime integration document.** It does not authorize the deployment of any new connector or worker agent.
- **This is NOT a tool shopping list.** It maps external *patterns*, not specific vendor demos.

## 2. Design Principles for Inspiration Absorption

When reviewing external multi-agent systems, HONGSTR applies the following filters:

- **Architecture First, Implementation Later**: Understand the flow of authority before writing prompts or Python scripts.
- **Absorb Patterns, Not Demos**: Focus on the underlying topology (e.g., Planner-Executor split) rather than flashy UI capabilities.
- **Role Before Tool**: Tools (like MCP or browser APIs) do not exist in a vacuum; they must be wielded by a specific Role subject to the Agent Roster contracts.
- **No Scope Explosion**: An external inspiration is only valid if it maps to an explicit internal gap.
- **Respect established Boundaries**: All proposals must remain strictly compliant with HONGSTR’s SSOT, read-only control plane, and report-only boundaries.
- **Backlog First, Rollout Later**: Valuable roles go onto the backlog for future `docs-first` adoption planning.

## 3. External Inspiration Patterns (High-Level Classification)

The broader AI engineering ecosystem frequently utilizes several core patterns. Here is how they are classified within HONGSTR:

### A. Planner / Executor Split

- **Concept**: A high-level agent decomposes tasks, while lower-level agents write code or execute tool calls.
- **HONGSTR Mapping**: *Already Partially Absorbed*. This maps to the `Chief Steward -> Lead Implementation Engineer` workflow described in the Agent Roster.

### B. MCP / Standardized Connector Intake

- **Concept**: Agents using Model Context Protocol (MCP) or similar schemas to dynamically discover and query external systems (GitHub, Notion, Linear).
- **HONGSTR Mapping**: *Backlog Candidate*. Currently, HONGSTR relies on static `.env` secrets and hardcoded data fetching scripts. A dedicated "Intake Analyst" role could formalize this.

### C. RAG / Precedent / Evidence Retrieval

- **Concept**: Vector databases or BM25 search retrieving exact context from massive proprietary codebases or documentation before answering.
- **HONGSTR Mapping**: *Backlog Candidate*. Essential for scaling the `Reviewer` and `Governance Librarian` but currently missing a dedicated curation role to prevent context poisoning.

### D. Intelligence / External Source Collection

- **Concept**: Autonomous agents continuously scraping web APIs or news feeds to find alpha or sentiment signals.
- **HONGSTR Mapping**: *Backlog Candidate*. Highly relevant to the `Director of Quant Research`, but requires strict isolation to avoid pipeline pollution.

### E. Triage / Due Diligence Support

- **Concept**: Pre-screening incoming issues, PRs, or user requests before a human looks at them.
- **HONGSTR Mapping**: *Currently Trialing*. This is actively being tested via the `Reviewer Supplementation Advisory Trial`.

## 4. Proposed Backlog Roles

To absorb these patterns without violating the Roster, the following new roles are proposed for the backlog. They do not exist in runtime yet.

### Backlog Candidate 1: GitHub Intake Analyst

- **Why this role exists**: To safely handle MCP/Connector queries to GitHub, filtering issues and PR telemetry.
- **Which current gap it addresses**: Replaces brittle, monolithic webhook scripts with robust semantic querying.
- **Which current role it supports**: Chief Steward (for routing), Reviewer (for evidence).
- **Why it is backlog**: Requires establishing safe, read-only MCP connection protocols first.
- **Red-line constraints**: Must be strictly read-only. Cannot autonomously close issues or merge PRs.

### Backlog Candidate 2: Evidence Pack Curator (RAG Pipeline)

- **Why this role exists**: To maintain the vector/search indices of governance rules and past PR precedents.
- **Which current gap it addresses**: Prevents the Reviewer and Librarian from hallucinating rules or losing context on large PRs.
- **Which current role it supports**: Governance Librarian, Reviewer.
- **Why it is backlog**: Vector DB / RAG infrastructure is complex and introduces data staleness risks if not designed as an SSOT derivative.
- **Red-line constraints**: Can only ingest from `docs/*` and merged PR histories. Cannot ingest unverified web data.

### Backlog Candidate 3: External Intel Collector

- **Why this role exists**: To manage autonomous browser or API polling for market sentiment, narratives, and macro events.
- **Which current gap it addresses**: Quant Research currently relies on static price datasets; lacks semantic market context.
- **Which current role it supports**: Director of Quant Research.
- **Why it is backlog**: Unrestricted web scraping requires heavy sandboxing to prevent prompt injection or payload poisoning.
- **Red-line constraints**: Output must land strictly in `data/derived/` or `reports/`. Never allowed to trigger execution or mutate `data/state/*`.

## 5. Role Priority Tiering

To prevent scope explosion, capabilities are tiered:

- **Tier A (Now / Absorbed)**: Planner/Executor splits, basic Triage (currently covered by Roster and Reviewer Trials).
- **Tier B (Next)**: *Evidence Pack Curator*, *GitHub Intake Analyst*. These directly support the immediate bottleneck (Reviewer/Quality Assurance) and stabilize existing governance.
- **Tier C (Later)**: *External Intel Collector*. Valuable for alpha generation, but depends on mature sandboxing and robust external-connector governance.
- **Tier D (Not Recommended)**: (See Section 6).

## 6. Anti-Patterns (Not Recommended / Rejected)

The following popular external concepts explicitly conflict with HONGSTR governance and will **NOT** be added to the backlog:

- **Unrestricted Browser Autonomy**: Agents given a browser and told "go research X on the internet" without deterministic bounding. High risk of hallucination and prompt injection.
- **Runtime-Mutating Agent Teams**: Frameworks where agents autonomously rewrite and deploy `.py` code to fix runtime errors on the fly. Violates the firm "PR-as-smallest-unit" and "Zero Core Diffs" rules.
- **"Chat-Ops" Execution Overrides**: Granting models the ability to bypass SSOT state files by executing commands directly from Telegram based on conversational nuances.
- **Demo-Oriented Flashy Agents**: Multi-agent loops that talk to each other to solve generic puzzles without explicit human-defined handoffs or kill switches.

## 7. Relationship to Existing Documents

- **Agent Roster**: The canonical list of *active* or *approved* roles. Backlog roles here do not exist in the Roster until promoted.
- **Role × Model Fit Matrix**: Maps models to the Roster. Does not apply tracking to backlog roles yet.
- **Adoption Guidance**: Dictates deployment of active roles.
- **This Document**: Acts as the staging ground / waiting room for new architectural ideas, preventing them from polluting the main governance docs until strictly needed.

## 8. Next Hand-Off

Actionable steps regarding this Backlog:

- To adopt a Tier B role (e.g., *GitHub Intake Analyst*), a dedicated, small `docs-first` proposal PR must be opened to promote it to the Agent Roster.
- Do not attempt to implement these backlog roles in code immediately.
- Adhere strictly to the "one capability at a time" principle. Currently, the primary focus remains the `Reviewer Supplementation Advisory Trial`.
