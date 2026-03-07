---
description: HONGSTR Governance Actions Allowed
---

# Governance Actions Allowed

To ensure Antigravity can function as an effective governance & triage assistant without being paralyzed by its own red lines, the following external actions are **EXPLICITLY ALLOWED**, provided they do not involve modifying core code (`src/hongstr/**`) or `.env` files.

## 1. Linear Tracking

- ✅ **ALLOWED**: Reading Linear issues for triage.
- ✅ **ALLOWED**: Creating new Linear sandbox/provisional issues to track follow-up tasks.
- ✅ **ALLOWED**: Updating the status, priority, or comments of existing issues if explicitly assigned or requested.
- ❌ **FORBIDDEN**: Modifying the text of P0 core definition cards without human approval.

## 2. GitHub Bounded Delivery

- ✅ **ALLOWED**: Creating branches (e.g., `codex/antigravity-xyz`).
- ✅ **ALLOWED**: Committing allowed files (`docs/**`, `.agent/**`) and pushing to origin.
- ✅ **ALLOWED**: Creating Pull Requests via `gh pr create`.
- ✅ **ALLOWED**: Reading PR diffs and performing code reviews against governance checklists.
- ❌ **FORBIDDEN**: Merging PRs directly (No auto-merge).
- ❌ **FORBIDDEN**: Creating a PR that includes modifications to `src/hongstr/**`, state semantics, or ETL/backfill pipelines.

## 3. Communication & Handoff

- ✅ **ALLOWED**: Outputting a `hongstr-handoff-to-codex.md` note.
- ✅ **ALLOWED**: Noting `[Linear pending/manual follow-up required]` in a PR body if the environment does not allow direct Linear API access.

## Summary Principle

**External Governance Actions (Linear APIs, GitHub APIs) != Core-Path Execution.**
Performing tracking and delivery operations is fully allowed and necessary to complete a bounded task smoothly.
