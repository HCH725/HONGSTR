# CCPM Governance Adoption for HONGSTR

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
| PR         | GitHub Pull Request              | Agent via `/dispatch`, referencing Task |

**No PR may land without at least one Task Issue reference.**

---

## HONGSTR-Specific Rules

1. **Allowed Paths Gate**: dispatchable Tasks must declare `allowed_paths:` in the issue body. The dispatcher reads this field to bound the changeset. Any diff outside declared paths is rejected.
2. **red-line check**: All PRs auto-run `bash scripts/guardrail_check.sh`. Core diff to `src/hongstr` must be zero.
3. **docs-only detection**: Issues with label `docs-only` skip the core-diff check and may be auto-merged if repo policy allows.
4. **report_only**: All research changes must include `report_only: true` in their task body.
5. **Rollback**: Every task must include a `Rollback:` section with a specific `git revert <sha>` command.

---

## Workflow Integration (Existing Dispatch)

The existing `.github/workflows/dispatch.yml` picks up `/dispatch` comments.
A Task Issue body that includes the fields from `.github/ISSUE_TEMPLATE/task.yml` (especially `allowed_paths`)
will surface those fields during dispatch so the agent can self-bound its changeset.

**Recommended enhancement (safe, no core change):**

- Add a label check: if the issue has `docs-only`, the dispatcher may run with `--docs-only` flag (no core diff allowed).
- Surface `acceptance_criteria:` from the issue body into the draft PR body automatically.

These are additive and do not modify dispatch semantics. See `docs/governance/acceptance_criteria.md` for the AC format.

---

## Rollback

All governance files are in `docs/governance/` and `.github/ISSUE_TEMPLATE/`.
To revert: `git revert <merge_commit>` — zero runtime impact since these are docs and templates only.
