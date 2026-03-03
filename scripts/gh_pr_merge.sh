#!/usr/bin/env bash
set -euo pipefail

# gh_pr_merge.sh
# Purpose: Create (or reuse) a PR for the current branch and request auto-merge via `gh`.
#
# Requirements:
#   - GitHub CLI installed: brew install gh
#   - Authenticated on this machine: gh auth login
#
# Usage:
#   bash scripts/gh_pr_merge.sh "PR title" "PR body"
#
# Merge strategy:
#   - Default: squash + delete branch
#   - Auto: waits for required checks / branch protection, then merges when ready

TITLE="${1:-}"
BODY="${2:-}"

if [[ -z "$TITLE" ]]; then
  echo "ERROR: missing PR title" >&2
  echo "Usage: bash scripts/gh_pr_merge.sh \"title\" \"body\"" >&2
  exit 2
fi
if [[ -z "$BODY" ]]; then
  BODY="Automated PR via gh."
fi

# Refuse to run on main
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$BRANCH" == "main" ]]; then
  echo "ERROR: refusing to open/merge PR from main branch" >&2
  exit 3
fi

# Ensure gh exists
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh not found. Install with: brew install gh" >&2
  exit 4
fi

# Ensure gh auth
if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh not authenticated on this machine. Run: gh auth login" >&2
  exit 5
fi

# Push current branch
git push -u origin HEAD

# Create PR if missing; else reuse existing
PR_URL=""
set +e
PR_URL="$(gh pr create --title "$TITLE" --body "$BODY" --base main --head "$BRANCH" 2>/dev/null)"
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  PR_URL="$(gh pr view "$BRANCH" --json url -q .url 2>/dev/null || true)"
fi

if [[ -z "$PR_URL" ]]; then
  echo "ERROR: unable to create or locate PR for branch: $BRANCH" >&2
  exit 6
fi

echo "PR_URL=$PR_URL"

# Request auto-merge. This will merge when checks pass & branch is up-to-date.
gh pr merge "$PR_URL" --squash --delete-branch --auto

echo "MERGE_REQUESTED_OK"
