# Phase B Auto-PR Ops Guide

This guide describes `scripts/auto_pr.sh` and `scripts/check_allowlist_changes.sh` for SSOT-safe automation.

## Safety Defaults

- Default behavior: **open PR only**, no auto-merge.
- Cooldown/dedupe: state file at `_local/state/auto_pr_state.json`.
- Allowlist enforcement:
  - `docs/**`
  - `_local/**`
  - `research/**`
  - `scripts/**` (non-prod semantics only)
- Hard block: staged `data/**` artifacts.

## Usage

```bash
# Dry-run: inspect what would be included
bash scripts/auto_pr.sh --dry-run --class ops-audit

# Open PR (default: no auto-merge)
bash scripts/auto_pr.sh \
  --class ops-audit \
  --cooldown-hours 24 \
  --generator "bash scripts/install_hongstr_skills.sh --force"

# Optional auto-merge mode (only when explicitly needed)
bash scripts/auto_pr.sh --class docs-only --auto-merge
```

## Allowlist Check Only

```bash
# Check worktree changes
bash scripts/check_allowlist_changes.sh --worktree --list-changed

# Check staged changes
bash scripts/check_allowlist_changes.sh --staged

# Check branch diff
bash scripts/check_allowlist_changes.sh --against-ref origin/main --list-changed
```

## Example Transcript Snippet

```text
$ bash scripts/auto_pr.sh --class skills-docs
[auto_pr] generator: bash scripts/install_hongstr_skills.sh --force
[auto_pr] PR created: https://github.com/HCH725/HONGSTR/pull/123
[auto_pr] auto-merge disabled (default). PR left open.
```

## Rollback

If merged changes need to be reverted:

```bash
git revert <merge_commit_sha>
git push
```
