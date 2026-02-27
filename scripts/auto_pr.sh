#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BASE_BRANCH="main"
COOLDOWN_HOURS="${AUTO_PR_COOLDOWN_HOURS:-24}"
ALLOW_DOCS_AUTOMERGE=0
RUN_PREFLIGHT=1
DRAFT_MODE=1
PRINT_NEXT_STEPS=0
ONLY_GENERATORS=()

usage() {
  cat <<'EOF'
Usage: bash scripts/auto_pr.sh [options]

Options:
  --base <branch>              Base branch to sync and open PR against (default: main)
  --cooldown-hours <hours>     Cooldown window for same change class (default: 24)
  --allow-docs-automerge       Allow docs-only PR auto-merge (default: off)
  --only <name>                Run only the named generator(s) from AUTO_PR_GENERATORS
  --print-next-steps           Print follow-up PR commands (ready/checks/merge) without executing them
  --skip-preflight             Skip preflight checks
  --draft                      Create draft PR (default)
  -h, --help                   Show this help

Environment:
  AUTO_PR_GENERATORS           Semicolon-separated generator specs:
                               - "name:command"
                               - "command" (backward compatible)
  AUTO_PR_STATE_FILE           State file path (default: _local/auto_pr/state.json)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base)
      BASE_BRANCH="$2"
      shift 2
      ;;
    --cooldown-hours)
      COOLDOWN_HOURS="$2"
      shift 2
      ;;
    --allow-docs-automerge)
      ALLOW_DOCS_AUTOMERGE=1
      shift
      ;;
    --only)
      ONLY_GENERATORS+=("$2")
      shift 2
      ;;
    --print-next-steps)
      PRINT_NEXT_STEPS=1
      shift
      ;;
    --skip-preflight)
      RUN_PREFLIGHT=0
      shift
      ;;
    --draft)
      DRAFT_MODE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

PY_BIN="${PY_BIN:-./.venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="python3"
fi

STATE_FILE="${AUTO_PR_STATE_FILE:-_local/auto_pr/state.json}"
mkdir -p "$(dirname "$STATE_FILE")"

sanitize_for_branch() {
  echo "$1" | tr -cs 'a-zA-Z0-9' '-'
}

is_expected_generator_output() {
  case "$1" in
    research/policy/regime_thresholds_candidate.json|docs/audits/regime_thresholds_calibration_*.json|docs/audits/regime_thresholds_calibration_*.md)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

print_dirty_tree_abort() {
  local dirty_raw="$1"
  local -a tracked_dirty=()
  local -a candidate_outputs=()
  local -a other_untracked=()
  local printed=0

  echo "[auto_pr] Working tree is dirty; aborting." >&2
  echo "[auto_pr] Dirty files (from git status --porcelain):" >&2
  while IFS= read -r line || [[ -n "${line:-}" ]]; do
    [[ -z "${line:-}" ]] && continue
    local status="${line:0:2}"
    local path="${line:3}"
    printf '  - %s\n' "$line" >&2
    printed=$((printed + 1))
    if [[ "$status" == "??" ]]; then
      if is_expected_generator_output "$path"; then
        candidate_outputs+=("$path")
      else
        other_untracked+=("$path")
      fi
    else
      tracked_dirty+=("$path")
    fi
  done <<< "$dirty_raw"

  if [[ "$printed" -eq 0 ]]; then
    echo "  - (none)" >&2
  fi

  if [[ "${#candidate_outputs[@]}" -gt 0 ]]; then
    echo "[auto_pr] Expected generator candidate outputs detected; safe cleanup commands:" >&2
    for path in "${candidate_outputs[@]}"; do
      echo "  rm -f \"$path\"" >&2
    done
  fi

  if [[ "${#tracked_dirty[@]}" -gt 0 ]]; then
    echo "[auto_pr] Tracked files changed; if unintended, restore selectively:" >&2
    for path in "${tracked_dirty[@]}"; do
      echo "  git checkout -- \"$path\"" >&2
    done
  fi

  if [[ "${#other_untracked[@]}" -gt 0 ]]; then
    echo "[auto_pr] Additional untracked files exist; review/remove manually before rerun." >&2
  fi
}

DIRTY_STATUS="$(git status --porcelain)"
if [[ -n "$DIRTY_STATUS" ]]; then
  print_dirty_tree_abort "$DIRTY_STATUS"
  exit 3
fi

echo "[auto_pr] Syncing $BASE_BRANCH ..."
git fetch origin
git checkout "$BASE_BRANCH"
git pull --ff-only origin "$BASE_BRANCH"

run_generator_cmd() {
  local run_cmd
  run_cmd="$(echo "$1" | xargs)"
  if [[ -z "$run_cmd" ]]; then
    return 0
  fi
  echo "[auto_pr] generator: $run_cmd"
  bash -lc "$run_cmd"
}

resolve_generator_command() {
  local name="$1"
  case "$name" in
    regime_thresholds_calibration)
      echo "bash scripts/calibrate_regime_thresholds.sh --pr-mode --as-of-utc \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\""
      ;;
    *)
      return 1
      ;;
  esac
}

run_named_or_inline_generator() {
  local gen_name="$1"
  local gen_cmd="$2"
  if [[ -z "$gen_cmd" ]]; then
    if ! gen_cmd="$(resolve_generator_command "$gen_name")"; then
      echo "[auto_pr] Unknown generator name: $gen_name" >&2
      exit 2
    fi
  fi
  run_generator_cmd "$gen_cmd"
}

if [[ -n "${AUTO_PR_GENERATORS:-}" || "${#ONLY_GENERATORS[@]}" -gt 0 ]]; then
  echo "[auto_pr] Running generators ..."
  RAW_GENERATORS=()
  while IFS= read -r _line || [[ -n "${_line:-}" ]]; do
    RAW_GENERATORS+=("$_line")
  done < <(printf '%s' "${AUTO_PR_GENERATORS:-}" | tr ';' '\n')

  if [[ "${#ONLY_GENERATORS[@]}" -eq 0 ]]; then
    for raw in "${RAW_GENERATORS[@]-}"; do
      spec="$(echo "$raw" | xargs)"
      if [[ -z "$spec" ]]; then
        continue
      fi
      if [[ "$spec" == *:* ]]; then
        gen_name="$(echo "${spec%%:*}" | xargs)"
        gen_cmd="$(echo "${spec#*:}" | xargs)"
        if [[ -z "$gen_name" ]]; then
          run_generator_cmd "$gen_cmd"
        else
          run_named_or_inline_generator "$gen_name" "$gen_cmd"
        fi
      else
        if cmd_from_name="$(resolve_generator_command "$spec" 2>/dev/null)"; then
          run_named_or_inline_generator "$spec" "$cmd_from_name"
        else
          run_generator_cmd "$spec"
        fi
      fi
    done
  else
    for only_name in "${ONLY_GENERATORS[@]-}"; do
      found=0
      for raw in "${RAW_GENERATORS[@]-}"; do
        spec="$(echo "$raw" | xargs)"
        if [[ -z "$spec" ]]; then
          continue
        fi
        if [[ "$spec" != *:* ]]; then
          continue
        fi
        gen_name="$(echo "${spec%%:*}" | xargs)"
        gen_cmd="$(echo "${spec#*:}" | xargs)"
        if [[ "$gen_name" == "$only_name" ]]; then
          run_named_or_inline_generator "$gen_name" "$gen_cmd"
          found=1
        fi
      done
      if [[ "$found" -eq 0 ]]; then
        run_named_or_inline_generator "$only_name" ""
      fi
    done
  fi
fi

CHANGED=()
while IFS= read -r _line || [[ -n "${_line:-}" ]]; do
  if [[ -n "$_line" ]]; then
    CHANGED+=("$_line")
  fi
done < <(
  {
    git diff --name-only
    git diff --name-only --cached
    git ls-files --others --exclude-standard
  } | sort -u
)

if [[ "${#CHANGED[@]}" -eq 0 ]]; then
  echo "[auto_pr] No changes detected. Exit 0."
  exit 0
fi

echo "[auto_pr] Changed files:"
printf '  - %s\n' "${CHANGED[@]}"

ALLOW_JSON=$(mktemp)
CLASS_JSON=$(mktemp)
CHANGED_LIST_FILE=$(mktemp)
trap 'rm -f "${ALLOW_JSON:-}" "${CLASS_JSON:-}" "${CHANGED_LIST_FILE:-}" "${PREFLIGHT_TXT:-}" "${BODY_FILE:-}"' EXIT
printf '%s\n' "${CHANGED[@]}" > "$CHANGED_LIST_FILE"

printf '%s\n' "${CHANGED[@]}" | "$PY_BIN" scripts/auto_pr_utils.py check > "$ALLOW_JSON" || {
  echo "[auto_pr] Allowlist check failed:"
  cat "$ALLOW_JSON"
  exit 4
}

printf '%s\n' "${CHANGED[@]}" | "$PY_BIN" scripts/auto_pr_utils.py classify > "$CLASS_JSON"
KIND=$(
  cat "$CLASS_JSON" | "$PY_BIN" -c 'import sys,json; print(json.load(sys.stdin).get("kind","mixed-allowlist"))'
)
TITLE=$(
  cat "$CLASS_JSON" | "$PY_BIN" -c 'import sys,json; print(json.load(sys.stdin).get("title","ops(auto_pr): allowlisted mixed update"))'
)

echo "[auto_pr] Classified change: $KIND"

FINGERPRINT=$(printf '%s\n' "${CHANGED[@]}" | shasum -a 256 | awk '{print $1}')
NOW_TS=$(date -u +%s)

SKIP_REASON=$("$PY_BIN" - <<PY
import json
from pathlib import Path
state_path = Path("$STATE_FILE")
now_ts = int("$NOW_TS")
cooldown = int(float("$COOLDOWN_HOURS") * 3600)
kind = "$KIND"
fingerprint = "$FINGERPRINT"
if not state_path.exists():
    print("")
    raise SystemExit(0)
try:
    state = json.loads(state_path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
last_kind = str(state.get("last_kind", ""))
last_fp = str(state.get("last_fingerprint", ""))
last_ts = int(state.get("last_ts", 0) or 0)
if kind == last_kind and fingerprint == last_fp and (now_ts - last_ts) < cooldown:
    print(f"cooldown_active kind={kind} remaining_s={cooldown-(now_ts-last_ts)}")
else:
    print("")
PY
)

if [[ -n "$SKIP_REASON" ]]; then
  SKIP_KIND="$KIND"
  SKIP_REMAINING_S=0
  if [[ "$SKIP_REASON" =~ kind=([^[:space:]]+) ]]; then
    SKIP_KIND="${BASH_REMATCH[1]}"
  fi
  if [[ "$SKIP_REASON" =~ remaining_s=([0-9]+) ]]; then
    SKIP_REMAINING_S="${BASH_REMATCH[1]}"
  fi

  OPEN_PR_JSON="[]"
  CLASS_PREFIX="codex/auto-pr-$(sanitize_for_branch "$SKIP_KIND")"
  if command -v gh >/dev/null 2>&1; then
    if GH_OUTPUT=$(GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr list \
      --state open \
      --search "head:${CLASS_PREFIX}" \
      --json number,url,title,headRefName \
      --limit 20 2>/dev/null); then
      OPEN_PR_JSON="$GH_OUTPUT"
    fi
  fi

  "$PY_BIN" scripts/auto_pr_utils.py render-cooldown-message \
    --kind "$SKIP_KIND" \
    --remaining-s "$SKIP_REMAINING_S" \
    --open-pr-json "$OPEN_PR_JSON"
  exit 0
fi

sanitize_kind="$(sanitize_for_branch "$KIND")"
BRANCH="codex/auto-pr-${sanitize_kind}-$(date -u +%Y%m%d_%H%M%S)"

git checkout -b "$BRANCH"

git add -- "${CHANGED[@]}"

PREFLIGHT_TXT=$(mktemp)
if [[ "$RUN_PREFLIGHT" -eq 1 ]]; then
  {
    echo "bash scripts/install_hongstr_skills.sh --force"
    bash scripts/install_hongstr_skills.sh --force
    echo
    echo "./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py"
    ./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
    echo
    echo "./.venv/bin/python -m pytest -q research/**/tests"
    ./.venv/bin/python -m pytest -q research/**/tests
    echo
    echo "git diff --name-only origin/main...HEAD | rg '^src/hongstr/' && exit 1 || true"
    git diff --name-only origin/main...HEAD | rg '^src/hongstr/' && exit 1 || true
    echo
    echo "rg -n 'subprocess|os.system|Popen' _local/telegram_cp/tg_cp_server.py && exit 1 || true"
    rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py && exit 1 || true
    echo
    echo "git status --porcelain | rg '^.. data/' && exit 1 || true"
    git status --porcelain | rg '^.. data/' && exit 1 || true
  } > "$PREFLIGHT_TXT" 2>&1
else
  echo "preflight skipped (--skip-preflight)" > "$PREFLIGHT_TXT"
fi

COMMIT_MSG="$TITLE"
git commit -m "$COMMIT_MSG"
git push -u origin "$BRANCH"

BODY_FILE=$(mktemp)
"$PY_BIN" scripts/auto_pr_utils.py render-pr-body \
  --title "$TITLE" \
  --paths-file "$CHANGED_LIST_FILE" \
  --preflight-file "$PREFLIGHT_TXT" \
  > "$BODY_FILE"

PR_ARGS=(--base "$BASE_BRANCH" --head "$BRANCH" --title "[codex] $TITLE" --body-file "$BODY_FILE")
if [[ "$DRAFT_MODE" -eq 1 ]]; then
  PR_ARGS=(--draft "${PR_ARGS[@]}")
fi

PR_URL=$(GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create "${PR_ARGS[@]}")
echo "[auto_pr] PR created: $PR_URL"

if [[ "$PRINT_NEXT_STEPS" -eq 1 ]]; then
  PR_NUMBER=$("$PY_BIN" - <<PY
import re
url = "$PR_URL"
match = re.search(r"/pull/(\\d+)", url)
print(match.group(1) if match else "")
PY
)
  echo "[auto_pr] Next steps (semi-auto; not executed):"
  if [[ "$DRAFT_MODE" -eq 1 && -n "$PR_NUMBER" ]]; then
    echo "  gh pr ready $PR_NUMBER"
  elif [[ "$DRAFT_MODE" -eq 1 ]]; then
    echo "  gh pr ready <pr_number>"
  fi
  if [[ -n "$PR_NUMBER" ]]; then
    echo "  gh pr checks $PR_NUMBER --watch"
    echo "  gh pr merge $PR_NUMBER --squash --delete-branch"
  else
    echo "  gh pr checks <pr_number> --watch"
    echo "  gh pr merge <pr_number> --squash --delete-branch"
  fi
fi

if [[ "$ALLOW_DOCS_AUTOMERGE" -eq 1 && "$KIND" == "docs-only" ]]; then
  echo "[auto_pr] docs-only auto-merge requested; enabling squash auto-merge"
  gh pr merge --squash --auto "$PR_URL"
fi

"$PY_BIN" - <<PY
import json
from pathlib import Path
state_path = Path("$STATE_FILE")
state_path.parent.mkdir(parents=True, exist_ok=True)
state = {
    "last_kind": "$KIND",
    "last_fingerprint": "$FINGERPRINT",
    "last_ts": int("$NOW_TS"),
    "last_branch": "$BRANCH",
    "last_pr": "$PR_URL",
}
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
PY

echo "[auto_pr] done"
