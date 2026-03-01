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
AGENT_PROVIDER="${AGENT_PROVIDER:-openai}"
AGENT_MODEL="${AGENT_MODEL:-gpt-5.3-codex}"
MAX_TOKENS="${MAX_TOKENS:-4000}"
MAX_COST_USD="${MAX_COST_USD:-2.00}"

COMMENT_AUTHOR=""
HAS_DISPATCH_COMMAND="false"
AGENT_NAME=""
TASK_PRESENT="false"
FAILURE_REASON="dispatch failed before initialization"
FAILURE_INCLUDE_TEMPLATE="false"
PR_URL=""

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

post_failure_comment() {
  local body=""
  local run_url=""
  body="Dispatch blocked: $FAILURE_REASON"
  if [[ "$FAILURE_INCLUDE_TEMPLATE" == "true" ]]; then
    body="${body}"$'\n\n'"Allowed paths:"$'\n'"- docs/dispatcher_smoke.md"
  fi
  run_url="$(build_run_url)"
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
        post_failure_comment
      fi
    fi
  fi
  exit "$rc"
}

trap cleanup EXIT

collect_changed_paths() {
  local output_file="$1"
  {
    git diff --name-only
    git diff --cached --name-only
    git ls-files --others --exclude-standard
  } | sed '/^$/d' | sort -u > "$output_file"
}

enforce_allowed_paths_gate() {
  local paths_file="$1"
  local gate_name="$2"
  local gate_error_file="$meta_dir/allowed_paths_gate.err"
  if [[ ! -s "$paths_file" ]]; then
    return 0
  fi
  if ! python3 - "$allowed_paths_file" "$paths_file" <<'PY' 2> "$gate_error_file"
import fnmatch
import sys

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
        return fnmatch.fnmatch(norm_path, norm_pattern)
    return norm_path == norm_pattern


violations = [path for path in paths if not any(is_allowed(path, pattern) for pattern in patterns)]
if violations:
    print("\n".join(violations), file=sys.stderr)
    raise SystemExit(1)
PY
  then
    local disallowed_paths=""
    disallowed_paths="$(tr '\n' ' ' < "$gate_error_file" | sed 's/[[:space:]]\+/ /g; s/[[:space:]]$//')"
    FAILURE_INCLUDE_TEMPLATE="true"
    die "${gate_name} blocked: ${disallowed_paths}"
  fi
}

extract_patch_paths() {
  local patch_file="$1"
  local output_file="$2"
  python3 - "$patch_file" "$output_file" <<'PY'
import sys
from pathlib import Path

patch_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
lines = patch_path.read_text(encoding="utf-8", errors="replace").splitlines()
paths = []
seen = set()


def normalize(candidate: str) -> str:
    value = candidate.strip()
    if value == "/dev/null":
        return ""
    if value.startswith("a/") or value.startswith("b/"):
        value = value[2:]
    return value


for line in lines:
    if line.startswith("diff --git "):
        parts = line.split()
        if len(parts) >= 4:
            for item in (parts[3], parts[2]):
                path = normalize(item)
                if path and path not in seen:
                    seen.add(path)
                    paths.append(path)
            continue
    if line.startswith("+++ ") or line.startswith("--- "):
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            path = normalize(parts[1])
            if path and path not in seen:
                seen.add(path)
                paths.append(path)

output_path.write_text("\n".join(paths) + ("\n" if paths else ""), encoding="utf-8")
PY
}

ensure_smoke_path_allowed() {
  local target_path="$1"
  if ! python3 - "$target_path" "$allowed_paths_file" <<'PY'
import fnmatch
import sys

target = sys.argv[1].strip().strip("/")
patterns = [line.strip() for line in open(sys.argv[2], "r", encoding="utf-8") if line.strip()]


def is_allowed(path: str, pattern: str) -> bool:
    norm_pattern = pattern.strip().strip("`")
    if not norm_pattern:
        return False
    if norm_pattern.endswith("/**"):
        base = norm_pattern[:-3].rstrip("/")
        return target == base or target.startswith(base + "/")
    if norm_pattern.endswith("/"):
        base = norm_pattern.rstrip("/")
        return target == base or target.startswith(base + "/")
    if any(ch in norm_pattern for ch in "*?["):
        return fnmatch.fnmatch(target, norm_pattern)
    return target == norm_pattern


if any(is_allowed(target, pattern) for pattern in patterns):
    raise SystemExit(0)
raise SystemExit(1)
PY
  then
    FAILURE_INCLUDE_TEMPLATE="true"
    die "$target_path is outside Allowed paths for issue #$ISSUE_NUMBER"
  fi
}

write_smoke_stub() {
  local timestamp_utc="$1"
  mkdir -p "$(dirname "$SMOKE_PATH")"
  {
    printf "# Dispatcher Smoke\n\n"
    printf "This file is updated by the guarded issue-comment dispatcher.\n\n"
    printf -- "- Issue: #%s\n" "$ISSUE_NUMBER"
    printf -- "- Actor: %s\n" "$COMMENT_AUTHOR"
    printf -- "- Updated UTC: %s\n" "$timestamp_utc"
    printf '%s\n' '- Allowed paths:'
    while IFS= read -r allowed_path; do
      [[ -n "$allowed_path" ]] || continue
      printf "  - %s\n" "$allowed_path"
    done < "$allowed_paths_file"
  } > "$SMOKE_PATH"
  git add "$SMOKE_PATH"
}

open_dispatch_pr() {
  local mode_label="$1"
  local pr_title="$2"
  local pr_body_file="$3"
  local pr_log_file="$4"

  if ! PR_URL="$(GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --draft --repo "$REPO_FULL_NAME" --base "$BASE_BRANCH" --head "$branch_name" --title "$pr_title" --body-file "$pr_body_file" 2> "$pr_log_file")"; then
    local pr_error=""
    pr_error="$(tr '\n' ' ' < "$pr_log_file" | sed 's/[[:space:]]\+/ /g; s/[[:space:]]$//' | cut -c1-220)"
    FAILURE_INCLUDE_TEMPLATE="true"
    if [[ -n "$pr_error" ]]; then
      die "dispatcher could not create a draft PR: $pr_error"
    fi
    die "dispatcher could not create a draft PR (check repo permissions or branch policy)"
  fi

  if [[ -z "$PR_URL" ]]; then
    FAILURE_INCLUDE_TEMPLATE="true"
    die "gh pr create did not return a PR URL"
  fi

  gh issue comment "$ISSUE_NUMBER" --repo "$REPO_FULL_NAME" --body "Dispatch ${mode_label} PR created for issue #$ISSUE_NUMBER: $PR_URL"
}

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
from __future__ import annotations

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


def strip_list_prefix(text: str) -> str:
    value = text.strip()
    value = re.sub("^(?:\\u2022|[-*+])\\s*", "", value)
    value = re.sub(r"^\d+\.\s*", "", value)
    return value.strip()


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
                candidate = strip_list_prefix(trailing).strip("`")
                if candidate:
                    allowed.append(candidate)
            continue

        if not in_section:
            continue

        if stripped and re.match(r"^\s{0,3}(?:#{1,6}\s*)?[A-Za-z][A-Za-z0-9 _:/\-]*:\s*$", line):
            break
        if stripped.startswith("#"):
            break
        if not stripped:
            if allowed:
                break
            continue

        candidate = strip_list_prefix(stripped).strip("`")
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


def parse_section_lines(body: str, name: str) -> list[str]:
    lines = body.splitlines()
    target = name.lower()
    in_section = False
    values: list[str] = []
    heading_re = re.compile(r"^\s{0,3}(?:#{1,6}\s*)?([A-Za-z][A-Za-z0-9 _/\-]*)\s*:\s*(.*)$")

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        match = heading_re.match(line)
        if match:
            heading_name = match.group(1).strip().lower()
            trailing = match.group(2).strip()
            if in_section and heading_name != target:
                break
            if heading_name == target:
                in_section = True
                if trailing:
                    values.append(strip_list_prefix(trailing))
                continue
        if not in_section:
            continue
        if stripped.startswith("#"):
            break
        if not stripped:
            if values:
                break
            continue
        values.append(strip_list_prefix(stripped))

    return [value for value in values if value]


agent_lines = parse_section_lines(issue_body, "Agent")
agent_name = agent_lines[0].strip().lower() if agent_lines else ""
task_lines = parse_section_lines(issue_body, "Task") or parse_section_lines(issue_body, "Agent plan")

meta = {
    "ISSUE_NUMBER": str(issue.get("number") or ""),
    "COMMENT_AUTHOR": str((comment.get("user") or {}).get("login") or ""),
    "REPO_FULL_NAME": str(repo.get("full_name") or ""),
    "HAS_DISPATCH_COMMAND": "true" if "/dispatch" in comment_body else "false",
    "AGENT_NAME": agent_name,
    "TASK_PRESENT": "true" if task_lines else "false",
}

with meta_env_path.open("w", encoding="utf-8") as handle:
    for key, value in meta.items():
        handle.write(f"{key}={shlex.quote(value)}\n")

with allowed_path.open("w", encoding="utf-8") as handle:
    for item in parse_allowed_paths(issue_body):
        handle.write(item + "\n")
PY

source "$meta_env"

if [[ -z "$ISSUE_NUMBER" ]]; then
  FAILURE_INCLUDE_TEMPLATE="true"
  die "issue number could not be determined from the event payload"
fi

if [[ -z "$REPO_FULL_NAME" ]]; then
  FAILURE_INCLUDE_TEMPLATE="true"
  die "repository name could not be determined from the event payload"
fi

if [[ "$HAS_DISPATCH_COMMAND" != "true" ]]; then
  FAILURE_INCLUDE_TEMPLATE="true"
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
  FAILURE_INCLUDE_TEMPLATE="true"
  die "comment author $COMMENT_AUTHOR is not allowlisted for /dispatch"
fi

ensure_label "$LABEL_RUNNING" "1D76DB" "Dispatch workflow is currently running."
ensure_label "$LABEL_DONE" "2DA44E" "Dispatch workflow completed successfully."
ensure_label "$LABEL_BLOCKED" "D1242F" "Dispatch workflow was blocked by a safety check."

remove_issue_label "$LABEL_DONE"
remove_issue_label "$LABEL_BLOCKED"
add_issue_label "$LABEL_RUNNING"

if [[ ! -s "$allowed_paths_file" ]]; then
  FAILURE_INCLUDE_TEMPLATE="true"
  die "issue #$ISSUE_NUMBER is missing an Allowed paths section"
fi

has_agent_mode="false"
if [[ -n "$AGENT_NAME" ]]; then
  case "$AGENT_NAME" in
    codex|antigravity)
      has_agent_mode="true"
      ;;
    *)
      FAILURE_INCLUDE_TEMPLATE="true"
      die "Agent section must be one of: codex, antigravity"
      ;;
  esac
fi

if [[ "$has_agent_mode" == "true" && "$TASK_PRESENT" != "true" ]]; then
  FAILURE_INCLUDE_TEMPLATE="true"
  die "Agent mode requires a Task section"
fi

timestamp_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
branch_name="codex/dispatch-issue-${ISSUE_NUMBER}-$(date -u +%Y%m%dT%H%M%SZ)-${GITHUB_RUN_ID:-local}"

git checkout -b "$branch_name"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

if [[ "$has_agent_mode" == "true" ]]; then
  mkdir -p tmp
  agent_patch_file="tmp/dispatch_agent_patch_${ISSUE_NUMBER}_${GITHUB_RUN_ID:-local}.diff"
  agent_log_file="$meta_dir/agent_run.stderr"
  patch_paths_file="$meta_dir/patch_paths.txt"
  changed_file_list="$meta_dir/changed_files.txt"
  apply_log_file="$meta_dir/git_apply.stderr"
  pr_create_log="$meta_dir/gh_pr_create.stderr"

  if ! bash scripts/agent_run.sh "$EVENT_PATH" "$allowed_paths_file" > "$agent_patch_file" 2> "$agent_log_file"; then
    local_agent_error="$(tr '\n' ' ' < "$agent_log_file" | sed 's/[[:space:]]\+/ /g; s/[[:space:]]$//' | cut -c1-220)"
    FAILURE_INCLUDE_TEMPLATE="true"
    if [[ -n "$local_agent_error" ]]; then
      die "$local_agent_error"
    fi
    die "agent runner failed"
  fi

  if [[ ! -s "$agent_patch_file" ]]; then
    FAILURE_INCLUDE_TEMPLATE="true"
    die "agent runner produced an empty patch"
  fi

  extract_patch_paths "$agent_patch_file" "$patch_paths_file"
  if [[ ! -s "$patch_paths_file" ]]; then
    FAILURE_INCLUDE_TEMPLATE="true"
    die "agent patch did not include any file paths"
  fi

  enforce_allowed_paths_gate "$patch_paths_file" "allowed_paths_diff_gate"

  if ! git apply --check "$agent_patch_file" 2> "$apply_log_file"; then
    apply_error="$(tr '\n' ' ' < "$apply_log_file" | sed 's/[[:space:]]\+/ /g; s/[[:space:]]$//' | cut -c1-220)"
    FAILURE_INCLUDE_TEMPLATE="true"
    if [[ -n "$apply_error" ]]; then
      die "git apply rejected the agent patch: $apply_error"
    fi
    die "git apply rejected the agent patch"
  fi

  git apply --index "$agent_patch_file"
  bash scripts/guardrail_check.sh

  collect_changed_paths "$changed_file_list"
  enforce_allowed_paths_gate "$changed_file_list" "allowed_paths_diff_gate"

  if git diff --cached --quiet; then
    FAILURE_INCLUDE_TEMPLATE="true"
    die "agent patch did not produce any staged changes"
  fi

  git commit -m "dispatch: agent patch for issue #$ISSUE_NUMBER"
  git push -u origin "$branch_name"

  cat > "$pr_body_file" <<EOF
## What
- Apply an auto-generated patch for issue #$ISSUE_NUMBER
- Agent: $AGENT_NAME
- Allowed paths were enforced before patch apply and again on the final diff

## Why
- Execute the requested issue task through the guarded dispatcher agent flow

## Risk
- Medium: machine-generated patch, but constrained to Allowed paths and held behind a draft PR

## Safety statement
- Actor allowlist was enforced before execution
- Allowed paths were mandatory and diff-gated
- scripts/guardrail_check.sh passed before the PR was opened
- This flow does not auto-merge

## Rollback
- Close this PR without merging

## How to verify
- Confirm the diff stays inside the issue's Allowed paths
- Confirm the issue thread contains the draft PR URL
EOF

  open_dispatch_pr "agent" "[dispatch][${AGENT_NAME}] Issue #$ISSUE_NUMBER auto patch" "$pr_body_file" "$pr_create_log"
else
  ensure_smoke_path_allowed "$SMOKE_PATH"
  write_smoke_stub "$timestamp_utc"
  bash scripts/guardrail_check.sh

  changed_file_list="$meta_dir/changed_files.txt"
  pr_create_log="$meta_dir/gh_pr_create.stderr"
  collect_changed_paths "$changed_file_list"
  enforce_allowed_paths_gate "$changed_file_list" "allowed_paths_diff_gate"

  if git diff --cached --quiet; then
    FAILURE_INCLUDE_TEMPLATE="true"
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

  open_dispatch_pr "smoke" "[dispatch] Issue #$ISSUE_NUMBER smoke PR" "$pr_body_file" "$pr_create_log"
fi

FAILURE_REASON=""
