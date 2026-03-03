# PR / SSOT Flow (Dev)

Policy SSOT: `docs/skills/global_red_lines.md`

## Branching
- Use `codex/<topic>-<UTC timestamp>` for agent branches.

## Scope discipline
- Keep PRs minimal and single-purpose.
- Avoid mixed refactors across planes in one PR.

## GitHub SSOT flow
1. Create branch from `main`.
2. Implement change.
3. Run required verification checks.
4. Commit + push + PR.
5. Merge via squash after checks are green.

## Plan B helper
- Preferred helper: `bash scripts/gh_pr_merge.sh "<title>" "<body>"`
- Fallback: `gh pr create` + `gh pr checks --watch` + `gh pr merge --squash --delete-branch`

## Rollback
- `git revert <merge_commit_sha>`
