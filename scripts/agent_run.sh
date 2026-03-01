#!/usr/bin/env bash
set -euo pipefail

DEFAULT_AGENT_PROVIDER="openai"
DEFAULT_AGENT_MODEL="gpt-5.3-codex"
DEFAULT_MAX_TOKENS="4000"
DEFAULT_MAX_COST_USD="2.00"
DEFAULT_INPUT_COST_PER_1M="5.00"
DEFAULT_OUTPUT_COST_PER_1M="15.00"

fail() {
  echo "$1" >&2
  exit 1
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    fail "$cmd is required for scripts/agent_run.sh"
  fi
}

EVENT_PATH="${1:-}"
ALLOWED_PATHS_FILE="${2:-}"

[[ -n "$EVENT_PATH" && -f "$EVENT_PATH" ]] || fail "event payload path is required"
[[ -n "$ALLOWED_PATHS_FILE" && -f "$ALLOWED_PATHS_FILE" ]] || fail "allowed paths file is required"

require_cmd curl
require_cmd python3
require_cmd git

AGENT_PROVIDER="${AGENT_PROVIDER:-$DEFAULT_AGENT_PROVIDER}"
AGENT_MODEL="${AGENT_MODEL:-$DEFAULT_AGENT_MODEL}"
MAX_TOKENS="${MAX_TOKENS:-$DEFAULT_MAX_TOKENS}"
MAX_COST_USD="${MAX_COST_USD:-$DEFAULT_MAX_COST_USD}"
OPENAI_INPUT_COST_PER_1M="${OPENAI_INPUT_COST_PER_1M:-$DEFAULT_INPUT_COST_PER_1M}"
OPENAI_OUTPUT_COST_PER_1M="${OPENAI_OUTPUT_COST_PER_1M:-$DEFAULT_OUTPUT_COST_PER_1M}"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$repo_root" ]] || fail "scripts/agent_run.sh must run inside a git checkout"
cd "$repo_root"

mkdir -p tmp
tmp_dir="$(mktemp -d "tmp/agent_run.XXXXXX")"
request_json="$tmp_dir/request.json"
response_json="$tmp_dir/response.json"
meta_json="$tmp_dir/meta.json"

if ! python3 - "$MAX_TOKENS" "$MAX_COST_USD" "$OPENAI_INPUT_COST_PER_1M" "$OPENAI_OUTPUT_COST_PER_1M" <<'PY'
import sys

for idx, name in enumerate(("MAX_TOKENS", "MAX_COST_USD", "OPENAI_INPUT_COST_PER_1M", "OPENAI_OUTPUT_COST_PER_1M"), start=1):
    raw = sys.argv[idx]
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be numeric: {exc}")
    if value <= 0:
        raise SystemExit(f"{name} must be greater than 0")
PY
then
  fail "invalid agent budget configuration"
fi

if ! python3 - "$EVENT_PATH" "$ALLOWED_PATHS_FILE" "$request_json" "$meta_json" <<'PY'
from __future__ import annotations

import fnmatch
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

event_path = Path(sys.argv[1])
allowed_paths_path = Path(sys.argv[2])
request_json_path = Path(sys.argv[3])
meta_json_path = Path(sys.argv[4])

payload = json.loads(event_path.read_text(encoding="utf-8"))
issue = payload.get("issue") or {}
issue_body = str(issue.get("body") or "")
issue_title = str(issue.get("title") or "")

agent_provider = os.environ.get("AGENT_PROVIDER", "openai")
agent_model = os.environ.get("AGENT_MODEL", "gpt-5.3-codex")
max_tokens = int(float(os.environ.get("MAX_TOKENS", "4000")))


def normalize_pattern(pattern: str) -> str:
    return pattern.strip().strip("`").replace("\\", "/")


def strip_list_prefix(text: str) -> str:
    value = text.strip()
    value = re.sub(r"^[•\-*+]\s*", "", value)
    value = re.sub(r"^\d+\.\s*", "", value)
    return value.strip()


def parse_section_lines(body: str, name: str) -> list[str]:
    lines = body.splitlines()
    target = name.lower()
    in_section = False
    values: list[str] = []
    heading_re = re.compile(r"^\s{0,3}(?:#{1,6}\s*)?([A-Za-z][A-Za-z0-9 _/\-]*)\s*:\s*(.*)$")

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        match = heading_re.match(line)
        if match:
            heading_name = match.group(1).strip().lower()
            trailing = match.group(2)
            if in_section and heading_name != target:
                break
            if heading_name == target:
                in_section = True
                trailing = trailing.strip()
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


def is_allowed(path: str, pattern: str) -> bool:
    norm_path = path.strip().strip("/")
    norm_pattern = normalize_pattern(pattern)
    if not norm_path or not norm_pattern:
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


allowed_patterns = [normalize_pattern(line) for line in allowed_paths_path.read_text(encoding="utf-8").splitlines() if line.strip()]
if not allowed_patterns:
    raise SystemExit("allowed paths file is empty")

agent_lines = parse_section_lines(issue_body, "Agent")
agent_name = agent_lines[0].strip().lower() if agent_lines else ""
if not agent_name:
    raise SystemExit("Agent section is required for agent mode")
if agent_name not in {"codex", "antigravity"}:
    raise SystemExit("Agent section must be one of: codex, antigravity")

task_lines = parse_section_lines(issue_body, "Task") or parse_section_lines(issue_body, "Agent plan")
if not task_lines:
    raise SystemExit("Task section is required for agent mode")
task_text = "\n".join(task_lines)

try:
    tracked_files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
except Exception:
    tracked_files = []

context_candidates: list[str] = []
seen: set[str] = set()
for pattern in allowed_patterns:
    matched = False
    for tracked in tracked_files:
        if is_allowed(tracked, pattern):
            matched = True
            if tracked not in seen:
                seen.add(tracked)
                context_candidates.append(tracked)
    if not matched and not any(ch in pattern for ch in "*?["):
        direct = pattern.rstrip("/")
        if direct and direct not in seen:
            seen.add(direct)
            context_candidates.append(direct)

context_blocks: list[str] = []
max_files = 20
max_bytes = 160000
bytes_used = 0

for rel_path in context_candidates[:max_files]:
    path = Path(rel_path)
    if not path.exists() or not path.is_file():
        context_blocks.append(f"FILE: {rel_path}\nSTATUS: missing (may be created if it remains inside Allowed paths)")
        continue
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        context_blocks.append(f"FILE: {rel_path}\nSTATUS: unreadable ({exc})")
        continue

    remaining = max_bytes - bytes_used
    if remaining <= 0:
        break
    trimmed = content[:remaining]
    truncated = len(trimmed) < len(content)
    bytes_used += len(trimmed)
    suffix = "\n[truncated]\n" if truncated else "\n"
    context_blocks.append(f"FILE: {rel_path}\n-----\n{trimmed}{suffix}-----")

if not context_blocks:
    context_blocks.append("No existing allowed-path files were found in the working tree.")

prompt = (
    "Generate a git unified diff patch only.\n"
    "Do not include prose, markdown fences, commentary, or any text outside the patch.\n"
    "Do not touch src/hongstr/**, data/**, logs/**, *.parquet, or *.pkl.\n"
    "Modify only files that match the Allowed paths list.\n"
    "Do not add files outside Allowed paths.\n"
    "If no safe patch is possible, return an empty string.\n\n"
    f"Repository: {payload.get('repository', {}).get('full_name', '')}\n"
    f"Issue title: {issue_title}\n"
    f"Requested agent persona: {agent_name}\n"
    "Allowed paths:\n"
    + "\n".join(f"- {pattern}" for pattern in allowed_patterns)
    + "\n\nTask:\n"
    + task_text
    + "\n\nFull issue body:\n"
    + issue_body
    + "\n\nAllowed-path file context:\n"
    + "\n\n".join(context_blocks)
)

estimated_prompt_tokens = max(1, math.ceil(len(prompt) / 4))

request_payload = {
    "model": agent_model,
    "messages": [
        {
            "role": "system",
            "content": "You are a repository patch generator. Return only a valid unified git diff patch.",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ],
    "temperature": 0,
    "max_completion_tokens": max_tokens,
}

request_json_path.write_text(json.dumps(request_payload, ensure_ascii=False), encoding="utf-8")
meta_json_path.write_text(
    json.dumps(
        {
            "agent_provider": agent_provider,
            "agent_model": agent_model,
            "agent_name": agent_name,
            "task_text": task_text,
            "issue_title": issue_title,
            "estimated_prompt_tokens": estimated_prompt_tokens,
            "allowed_patterns": allowed_patterns,
        },
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
PY
then
  fail "agent prompt build failed"
fi

if ! python3 - "$meta_json" "$MAX_COST_USD" "$MAX_TOKENS" "$OPENAI_INPUT_COST_PER_1M" "$OPENAI_OUTPUT_COST_PER_1M" <<'PY'
import json
import sys
from pathlib import Path

meta = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
max_cost = float(sys.argv[2])
max_tokens = float(sys.argv[3])
input_cost_per_1m = float(sys.argv[4])
output_cost_per_1m = float(sys.argv[5])

prompt_tokens = float(meta.get("estimated_prompt_tokens") or 0)
estimated_max_cost = ((prompt_tokens * input_cost_per_1m) + (max_tokens * output_cost_per_1m)) / 1_000_000.0
if estimated_max_cost > max_cost:
    raise SystemExit(
        f"budget gate blocked before API call: estimated max cost ${estimated_max_cost:.4f} exceeds MAX_COST_USD=${max_cost:.4f}"
    )
PY
then
  fail "budget gate blocked before API call"
fi

case "$AGENT_PROVIDER" in
  openai)
    [[ -n "${OPENAI_API_KEY:-}" ]] || fail "OPENAI_API_KEY is required for AGENT_PROVIDER=openai"
    openai_base_url="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
    if ! curl -fsS "${openai_base_url%/}/chat/completions" \
      -H "Authorization: Bearer ${OPENAI_API_KEY}" \
      -H "Content-Type: application/json" \
      -d @"$request_json" \
      > "$response_json"; then
      fail "openai API request failed"
    fi
    ;;
  *)
    fail "unsupported AGENT_PROVIDER: $AGENT_PROVIDER"
    ;;
esac

if ! python3 - "$response_json" "$meta_json" "$MAX_COST_USD" "$OPENAI_INPUT_COST_PER_1M" "$OPENAI_OUTPUT_COST_PER_1M" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

response = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
meta = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
max_cost = float(sys.argv[3])
input_cost_per_1m = float(sys.argv[4])
output_cost_per_1m = float(sys.argv[5])


def extract_text(payload: dict) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                    continue
                if item.get("type") == "text":
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        parts.append(text_value)
                    elif isinstance(text_value, dict) and isinstance(text_value.get("value"), str):
                        parts.append(text_value["value"])
            return "".join(parts)

    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    output = payload.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "output_text" and isinstance(block.get("text"), str):
                    parts.append(block["text"])
        return "".join(parts)

    return ""


def strip_code_fences(text: str) -> str:
    value = text.strip()
    if not value.startswith("```"):
        return value
    lines = value.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


usage = response.get("usage") or {}
prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("prompt_token_count")
completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or usage.get("completion_token_count")

if prompt_tokens is None:
    prompt_tokens = meta.get("estimated_prompt_tokens") or 0
if completion_tokens is None:
    completion_tokens = 0

prompt_tokens = float(prompt_tokens)
completion_tokens = float(completion_tokens)
actual_cost = ((prompt_tokens * input_cost_per_1m) + (completion_tokens * output_cost_per_1m)) / 1_000_000.0
if actual_cost > max_cost:
    raise SystemExit(f"budget gate blocked after API call: actual cost ${actual_cost:.4f} exceeds MAX_COST_USD=${max_cost:.4f}")

text = strip_code_fences(extract_text(response))
if not text:
    raise SystemExit("agent model returned an empty patch")

sys.stdout.write(text)
if not text.endswith("\n"):
    sys.stdout.write("\n")
PY
then
  fail "agent response processing failed"
fi
