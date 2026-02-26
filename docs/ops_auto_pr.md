# HONGSTR Ops: Auto-PR (Phase B)

This runbook describes the minimal viable Auto-PR flow for docs/meta updates.

## Scope and Guardrails

`scripts/auto_pr.sh` is designed for allowlisted, non-core updates only.

Hard constraints:
- do not modify `src/hongstr/**`
- do not commit `data/**`
- keep tg_cp no-exec policy
- keep report_only defaults
- GitHub PR flow is the SSOT path for changes

Allowed changed paths:
- `docs/**`
- `ops/**/*.md`

Anything outside this allowlist is blocked by:
- `scripts/check_allowlist_changes.sh`

## Commands

### 1) Validate changed files against allowlist

```bash
bash scripts/check_allowlist_changes.sh
```

Diff against a ref:

```bash
bash scripts/check_allowlist_changes.sh --against-ref origin/main
```

### 2) Run Auto-PR

Dry-run first:

```bash
bash scripts/auto_pr.sh --dry-run
```

With optional generators:

```bash
bash scripts/auto_pr.sh \
  --generator "bash scripts/install_hongstr_skills.sh --force"
```

Custom title/body:

```bash
bash scripts/auto_pr.sh \
  --title "docs: refresh ops audit notes" \
  --body "Automated docs-only refresh."
```

## What Auto-PR Does

1. Ensures clean worktree.
2. Syncs `main` with `origin/main`.
3. Creates a new branch: `codex/auto-pr-<UTC timestamp>`.
4. Runs optional generator commands.
5. Validates changed files are allowlisted.
6. If no changes: exits `0`.
7. Commits only allowlisted files.
8. Pushes branch and creates PR with safety + rollback notes.
9. Waits PR checks (`gh pr checks --watch`).
10. Squash-merges PR and deletes branch.
11. Syncs local `main` (`git pull --ff-only`).

## Change-Type Title Classification (B2 hardening)

Default PR title is auto-classified by changed paths:
- `ops-audit`
- `skills-docs`
- `docs-only`
- `docs-meta`

You can always override with `--title`.

## Rollback

After merge, rollback with:

```bash
git revert <merge_commit_sha>
git push
```

## Example Run Transcript (Copy/Paste)

```text
$ bash scripts/auto_pr.sh --dry-run
[auto_pr] dry-run complete.
  branch: codex/auto-pr-20260227_031245
  title : chore(auto-pr): docs-only update (20260227_031245)
  class : docs-only
  files :
    - docs/audits/example_audit.md

$ bash scripts/auto_pr.sh
[auto_pr] created PR: https://github.com/HCH725/HONGSTR/pull/123
[auto_pr] waiting for checks...
[auto_pr] checks passed; squash merging...
[auto_pr] done.
```
