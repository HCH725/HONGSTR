# CCPM Governance Adoption for HONGSTR

Status: historical governance note. Not canonical for the current single-entry model.
For current policy, use:

- `docs/architecture/agent_organization_governance_v1.md`
- `docs/architecture/direct_dispatch_retirement_v1.md`
- `docs/architecture/escalation_taxonomy_v1.md`
- `docs/architecture/legacy_keep_kill_merge_review_v1.md`
- `docs/architecture/governance_dedupe_record_v1.md`

## What is CCPM?

CCPM (Claude Code Project Management) brings **spec-driven development** into an AI-assisted workflow:
every PR must trace back to a specification. This prevents "vibe coding" where an agent freely makes
architectural decisions that should be human-owned.

In HONGSTR we adapt this with our existing constraints:

- `src/hongstr` core is red-lined — no agent changes without an approved PRD.
- `tg_cp` must remain read-only/no-exec — any change requires an explicit Epic with a safety gate.
- Research is report-only by default.

---

## Hierarchy

```
PRD (Problem Statement)
 └── Epic (Scope + Workstreams + Dependencies)
      └── Task (File-level checklist + tests + rollback)
           └── PR (Code change, must pass guardrail_check)
```

Every PR body must reference the Epic/Task GitHub Issue number: `Closes #<issue>`.

---

## Traceability Rules

| Artifact   | Location                         | Trigger           |
|------------|----------------------------------|-------------------|
| PRD        | GitHub Issue (`prd` label)       | Human authored    |
| Epic       | GitHub Issue (`epic` label)      | Human or agent, after PRD approval |
| Task       | GitHub Issue (`task` label)      | Agent, after Epic scoped |
| PR         | GitHub Pull Request              | Standard reviewed PR flow; the legacy direct `/dispatch` chain has been retired |

**No PR may land without at least one Task Issue reference.**

---

## HONGSTR-Specific Rules

1. **Allowed Paths Gate**: bounded repair or future automation paths, if any remain, must declare explicit `allowed_paths:` and stay separately reviewed. The legacy direct `/dispatch` chain has been retired.
2. **red-line check**: All PRs auto-run `bash scripts/guardrail_check.sh`. Core diff to `src/hongstr` must be zero.
3. **docs-only detection**: Issues with label `docs-only` skip the core-diff check and may be auto-merged if repo policy allows.
4. **report_only**: All research changes must include `report_only: true` in their task body.
5. **Rollback**: Every task must include a `Rollback:` section with a specific `git revert <sha>` command.

---

## Historical Direct Dispatch (Retired)

The legacy direct `/dispatch` chain has been retired. See:

- `docs/architecture/direct_dispatch_retirement_v1.md`
- `docs/architecture/legacy_dispatcher_ingress_review_v1.md`

This document no longer defines or recommends any issue-comment dispatch workflow.

## Current Governance Direction

- Telegram remains the single outward operator entrance
- SSOT refresh and deterministic fallback remain on the Stage 2 path
- report-only research and bounded repair remain separate from GitHub issue-comment dispatch

---

## Rollback

All governance files are in `docs/governance/` and `.github/ISSUE_TEMPLATE/`.
To revert: `git revert <merge_commit>` — zero runtime impact since these are docs and templates only.
