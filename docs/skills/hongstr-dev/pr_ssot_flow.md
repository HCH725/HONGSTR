# PR / SSOT Flow (Dev)

**MUST READ FIRST:** `docs/skills/global_red_lines.md`

## Branching
- Use descriptive branches: `antigravity/<topic>-YYYYMMDD`

## Commit discipline
- No generated `data/**` artifacts committed.
- Keep PRs focused; avoid “big refactor while fixing”.

## Plan B: gh CLI helper
- Use: `bash scripts/gh_pr_merge.sh "<title>" "<body>"`
- Must pass CI; rollback via `git revert <commit_sha>`
