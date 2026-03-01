#!/usr/bin/env bash
set -euo pipefail

LABEL_RUNNING="dispatch:running"
LABEL_DONE="dispatch:done"
LABEL_BLOCKED="dispatch:blocked"
DEFAULT_ALLOWLIST="HCH725"
DEFAULT_BASE_BRANCH="main"
SMOKE_PATH="docs/dispatcher_smoke.md"

ISSUE_NUMBER="${ISSUE_NUMBER:-}"
REPO_FULL_NAME="${DISPATCH_REPO:-${GITHUB_REPOSITORY:-}}"
EVENT_PATH="${GITHUB_EVENT_PATH:-}"
DISPATCH_ALLOWLIST="${DISPATCH_ALLOWLIST:-$DEFAULT_ALLOWLIST}"
BASE_BRANCH="${DISPATCH_BASE_BRANCH:-$DEFAULT_BASE_BRANCH}"
COMMENT_AUTHOR=""
HAS_DISPATCH_COMMAND="false"
FAILURE_REASON="dispatch failed before initialization"
PR_URL=""
FAILURE_NEEDS_TEMPLATE="false"

die() {
  FAILURE_REASON="$1"
  echo "::error::$1" >&2
  exit 1
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    die "$cmd is required for dispatcher execution"
  fi
}

build_run_url() {
  local repo_name="${REPO_FULL_NAME:-${GITHUB_REPOSITORY:-}}"
  local server_url="${GITHUB_SERVER_URL:-}"
  local run_id="${GITHUB_RUN_ID:-}"
  if [[ -z "$repo_name" || -z "$server_url" || -z "$run_id" ]]; then
    return 0
  fi
  printf '%s/%s/actions/runs/%s' "$server_url" "$repo_name" "$run_id"
}

post_init_failure_comment() {
  local run_url=""
  local body=""
  run_url="$(build_run_url)"
  body="Dispatch blocked: $FAILURE_REASON"
  body="${body}"$'\n\n'"Allowed paths:"$'\n'"- docs/dispatcher_smoke.md"
  if [[ -n "$run_url" ]]; then
    body="${body}"$'\n\n'"Actions run: $run_url"
  fi
  gh issue comment "$ISSUE_NUMBER" --repo "$REPO_FULL_NAME" --body "$body" >/dev/null 2>&1 || true
}

ensure_label() {
  local label_name="$1"
  local label_color="$2"
  local label_description="$3"
  gh label create "$label_name" --repo "$REPO_FULL_NAME" --color "$label_color" --description "$label_description" >/dev/null 2>&1 || true
}

add_issue_label() {
  local label_name="$1"
  gh issue edit "$ISSUE_NUMBER" --repo "$REPO_FULL_NAME" --add-label "$label_name" >/dev/null 2>&1 || true
}

remove_issue_label() {
  local label_name="$1"
  gh issue edit "$ISSUE_NUMBER" --repo "$REPO_FULL_NAME" --remove-label "$label_name" >/dev/null 2>&1 || true
}

cleanup() {
  local rc=$?
  if [[ -n "$ISSUE_NUMBER" && -n "$REPO_FULL_NAME" ]]; then
    remove_issue_label "$LABEL_RUNNING"
    if [[ $rc -eq 0 ]]; then
      remove_issue_label "$LABEL_BLOCKED"
      add_issue_label "$LABEL_DONE"
    else
      remove_issue_label "$LABEL_DONE"
      add_issue_label "$LABEL_BLOCKED"
      if [[ -n "$FAILURE_REASON" ]]; then
        if [[ "$FAILURE_NEEDS_TEMPLATE" == "true" ]]; then
          post_init_failure_comment
        else
          gh issue comment "$ISSUE_NUMBER" --repo "$REPO_FULL_NAME" --body "Dispatch blocked for issue #$ISSUE_NUMBER: $FAILURE_REASON" >/dev/null 2>&1 || true
        fi
      fi
    fi
  fi
  exit "$rc"
}

trap cleanup EXIT

require_cmd gh
require_cmd git
require_cmd python3

[[ -n "$EVENT_PATH" && -f "$EVENT_PATH" ]] || die "GITHUB_EVENT_PATH is required"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$repo_root" ]] || die "dispatcher must run inside a git checkout"
cd "$repo_root"

meta_dir="$(mktemp -d)"
meta_env="$meta_dir/meta.env"
allowed_paths_file="$meta_dir/allowed_paths.txt"
pr_body_file="$meta_dir/pr_body.md"

python3 - "$EVENT_PATH" "$meta_env" "$allowed_paths_file" <<'PY'
import json
import re
import shlex
import sys
from pathlib import Path

event_path = Path(sys.argv[1])
meta_env_path = Path(sys.argv[2])
allowed_path = Path(sys.argv[3])
payload = json.loads(event_path.read_text(encoding="utf-8"))

issue = payload.get("issue") or {}
comment = payload.get("comment") or {}
repo = payload.get("repository") or {}
comment_body = str(comment.get("body") or "")
issue_body = str(issue.get("body") or "")


def parse_allowed_paths(body: str) -> list[str]:
    lines = body.splitlines()
    allowed: list[str] = []
    in_section = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        heading_match = re.match(r"^\s{0,3}(?:#{1,6}\s*)?Allowed paths\s*:?\s*(.*)$", line, re.IGNORECASE)
        if heading_match:
            in_section = True
            trailing = heading_match.group(1).strip()
            if trailing:
                candidate = re.sub(r"^[•\-*+]\s*", "", trailing)
                candidate = re.sub(r"^\d+\.\s*", "", candidate)
                candidate = candidate.strip().strip("`")
                if candidate:
                    allowed.append(candidate)
            continue

        if not in_section:
            continue

        if stripped and re.match(r"^\s{0,3}(?:#{1,6}\s*)?[A-Za-z][A-Za-z0-9 _:/-]*:\s*$", line):
            break
        if stripped.startswith("#"):
            break
        if stripped.lower() in {"forbidden", "forbidden paths", "rollback", "how to verify"}:
            break
        if not stripped:
            if allowed:
                break
            continue

        candidate = stripped
        candidate = re.sub(r"^[•\-*+] \[[ xX]\]\s*", "", candidate)
        candidate = re.sub(r"^[•\-*+]\s*", "", candidate)
        candidate = re.sub(r"^\d+\.\s*", "", candidate)
        candidate = candidate.strip().strip("`")
        if candidate:
            allowed.append(candidate)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in allowed:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


allowed_paths = parse_allowed_paths(issue_body)
meta = {
    "ISSUE_NUMBER": str(issue.get("number") or ""),
    "COMMENT_AUTHOR": str((comment.get("user") or {}).get("login") or ""),
    "REPO_FULL_NAME": str(repo.get("full_name") or ""),
    "HAS_DISPATCH_COMMAND": "true" if "/dispatch" in comment_body else "false",
}

with meta_env_path.open("w", encoding="utf-8") as handle:
    for key, value in meta.items():
        handle.write(f"{key}={shlex.quote(value)}\n")

with allowed_path.open("w", encoding="utf-8") as handle:
    for item in allowed_paths:
        handle.write(item + "\n")
PY

source "$meta_env"

if [[ -z "$ISSUE_NUMBER" ]]; then
  die "issue number could not be determined from the event payload"
fi

if [[ -z "$REPO_FULL_NAME" ]]; then
  die "repository name could not be determined from the event payload"
fi

if [[ "$HAS_DISPATCH_COMMAND" != "true" ]]; then
  die "issue comment does not contain /dispatch"
fi

author_allowed="false"
IFS=',' read -r -a allowlisted_authors <<< "$DISPATCH_ALLOWLIST"
for candidate in "${allowlisted_authors[@]}"; do
  trimmed="${candidate//[[:space:]]/}"
  if [[ -n "$trimmed" && "$COMMENT_AUTHOR" == "$trimmed" ]]; then
    author_allowed="true"
    break
  fi
done

if [[ "$author_allowed" != "true" ]]; then
  die "comment author $COMMENT_AUTHOR is not allowlisted for /dispatch"
fi

if [[ ! -s "$allowed_paths_file" ]]; then
  FAILURE_NEEDS_TEMPLATE="true"
  die "issue #$ISSUE_NUMBER is missing an Allowed paths section"
fi

ensure_label "$LABEL_RUNNING" "1D76DB" "Dispatch workflow is currently running."
ensure_label "$LABEL_DONE" "2DA44E" "Dispatch workflow completed successfully."
ensure_label "$LABEL_BLOCKED" "D1242F" "Dispatch workflow was blocked by a safety check."

remove_issue_label "$LABEL_DONE"
remove_issue_label "$LABEL_BLOCKED"
add_issue_label "$LABEL_RUNNING"

if ! python3 - "$SMOKE_PATH" "$allowed_paths_file" <<'PY'
import sys
from pathlib import PurePosixPath

target = sys.argv[1]
patterns = [line.strip() for line in open(sys.argv[2], "r", encoding="utf-8") if line.strip()]


def is_allowed(path: str, pattern: str) -> bool:
    norm_path = path.strip().strip("/")
    norm_pattern = pattern.strip()
    if not norm_pattern:
        return False
    norm_pattern = norm_pattern.strip("`")
    if norm_pattern.endswith("/**"):
        base = norm_pattern[:-3].rstrip("/")
        return norm_path == base or norm_path.startswith(base + "/")
    if norm_pattern.endswith("/"):
        base = norm_pattern.rstrip("/")
        return norm_path == base or norm_path.startswith(base + "/")
    if any(ch in norm_pattern for ch in "*?["):
        return PurePosixPath(norm_path).match(norm_pattern)
    return norm_path == norm_pattern


if any(is_allowed(target, pattern) for pattern in patterns):
    raise SystemExit(0)

print(f"{target} is outside Allowed paths", file=sys.stderr)
raise SystemExit(1)
PY
then
  FAILURE_NEEDS_TEMPLATE="true"
  die "$SMOKE_PATH is outside Allowed paths for issue #$ISSUE_NUMBER"
fi

timestamp_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
branch_name="codex/dispatch-issue-${ISSUE_NUMBER}-$(date -u +%Y%m%dT%H%M%SZ)-${GITHUB_RUN_ID:-local}"

git checkout -b "$branch_name"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

mkdir -p "$(dirname "$SMOKE_PATH")"
{
  printf "# Dispatcher Smoke\n\n"
  printf "This file is updated by the guarded issue-comment dispatcher.\n\n"
  printf "- Issue: #%s\n" "$ISSUE_NUMBER"
  printf "- Actor: %s\n" "$COMMENT_AUTHOR"
  printf "- Updated UTC: %s\n" "$timestamp_utc"
  printf "- Allowed paths:\n"
  while IFS= read -r allowed_path; do
    [[ -n "$allowed_path" ]] || continue
    printf "  - %s\n" "$allowed_path"
  done < "$allowed_paths_file"
} > "$SMOKE_PATH"

git add "$SMOKE_PATH"

bash scripts/guardrail_check.sh

changed_file_list="$meta_dir/changed_files.txt"
{
  git diff --name-only
  git diff --cached --name-only
  git ls-files --others --exclude-standard
} | sed '/^$/d' | sort -u > "$changed_file_list"

if ! python3 - "$allowed_paths_file" "$changed_file_list" <<'PY'
import sys
from pathlib import PurePosixPath

patterns = [line.strip() for line in open(sys.argv[1], "r", encoding="utf-8") if line.strip()]
paths = [line.strip() for line in open(sys.argv[2], "r", encoding="utf-8") if line.strip()]


def is_allowed(path: str, pattern: str) -> bool:
    norm_path = path.strip().strip("/")
    norm_pattern = pattern.strip().strip("`")
    if not norm_pattern:
        return False
    if norm_pattern.endswith("/**"):
        base = norm_pattern[:-3].rstrip("/")
        return norm_path == base or norm_path.startswith(base + "/")
    if norm_pattern.endswith("/"):
        base = norm_pattern.rstrip("/")
        return norm_path == base or norm_path.startswith(base + "/")
    if any(ch in norm_pattern for ch in "*?["):
        return PurePosixPath(norm_path).match(norm_pattern)
    return norm_path == norm_pattern


violations = [path for path in paths if not any(is_allowed(path, pattern) for pattern in patterns)]
if violations:
    print("\n".join(violations), file=sys.stderr)
    raise SystemExit(1)
PY
then
  disallowed_paths="$(tr '\n' ' ' < "$changed_file_list" | sed 's/[[:space:]]\+$//')"
  die "dispatcher modified paths outside Allowed paths: $disallowed_paths"
fi

if git diff --cached --quiet; then
  die "dispatcher did not produce any staged changes"
fi

git commit -m "docs: dispatcher smoke for issue #$ISSUE_NUMBER"
git push -u origin "$branch_name"

cat > "$pr_body_file" <<EOF
## What
- Create a guarded dispatcher smoke PR for issue #$ISSUE_NUMBER
- Change only $SMOKE_PATH within the issue's Allowed paths

## Why
- Exercise the issue-comment dispatcher through a PR-based flow

## Risk
- Low: docs-only stub change produced by the dispatcher

## Safety statement
- Dispatch is limited to issue comments containing /dispatch from allowlisted owners
- The staged diff was checked against the issue's Allowed paths before commit
- scripts/guardrail_check.sh passed before the PR was opened

## Rollback
- Close this PR without merging

## How to verify
- Confirm this PR changes only files listed in the issue's Allowed paths
- Confirm the originating issue received a bot comment containing this PR URL
EOF

if ! PR_URL="$(GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --draft --repo "$REPO_FULL_NAME" --base "$BASE_BRANCH" --head "$branch_name" --title "[dispatch] Issue #$ISSUE_NUMBER smoke PR" --body-file "$pr_body_file")"; then
  FAILURE_NEEDS_TEMPLATE="true"
  die "dispatcher could not create a draft PR (check repo permissions or branch policy)"
fi
if [[ -z "$PR_URL" ]]; then
  FAILURE_NEEDS_TEMPLATE="true"
  die "gh pr create did not return a PR URL"
fi

gh issue comment "$ISSUE_NUMBER" --repo "$REPO_FULL_NAME" --body "Dispatch PR created for issue #$ISSUE_NUMBER: $PR_URL"
FAILURE_REASON=""
