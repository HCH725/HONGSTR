# Phase B Auto-PR Hardening

This document describes the hardened Auto-PR flow for safe-tier changes only.

## Scope and Guardrails

Allowed paths:

- `docs/**`
- `research/**`
- `_local/**`
- `scripts/auto_pr.sh`
- `scripts/check_allowlist_changes.sh`

Blocked paths:

- `src/hongstr/**` (core semantic boundary)
- `data/**` (runtime artifacts)

## Policy Tiers

`scripts/auto_pr.sh` classifies pending changes into tiers:

1. `docs-only`
2. `research-local`
3. `ops-tooling`
4. `mixed-safe`

Merge policy:

- `docs-only`: can auto-merge only when `--auto-merge-docs-only` is explicitly set.
- all other tiers: PR opens only (manual review/merge).

## Cooldown / Dedupe

State file (default):

- `_local/state/auto_pr_state.json`

Per class, the script stores:

- last PR timestamp
- last fingerprint
- last PR URL

The script skips opening a new PR when:

- the fingerprint matches the previous class fingerprint (dedupe), or
- class cooldown window has not elapsed (default `24h`).

## Usage

```bash
# Open PR only (default)
bash scripts/auto_pr.sh --class auto

# Docs-only with optional auto-merge
bash scripts/auto_pr.sh --class docs-only --auto-merge-docs-only

# Include generator command(s)
bash scripts/auto_pr.sh \
  --class research-local \
  --generator "bash scripts/install_hongstr_skills.sh --force"
```

## Preflight Transcript in PR Body

The script embeds a transcript block with:

- skills install
- tg_cp smoke test
- research tests
- core diff guard
- tg_cp no-exec guard
- data staged guard

This appears automatically in the generated PR body.

## Rollback

```bash
git revert <merge_commit_sha>
git push
```
