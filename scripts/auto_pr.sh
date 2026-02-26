#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BASE_BRANCH="${BASE_BRANCH:-main}"
CHANGE_CLASS="${CHANGE_CLASS:-auto}"
COOLDOWN_HOURS="${COOLDOWN_HOURS:-24}"
STATE_FILE="${AUTO_PR_STATE_FILE:-_local/state/auto_pr_state.json}"
AUTO_MERGE_DOCS_ONLY=0
FORCE=0
DRY_RUN=0
SKIP_PREFLIGHT=0
PR_TITLE="${PR_TITLE:-}"
PR_BODY_FILE="${PR_BODY_FILE:-}"

GENERATOR_CMDS=()

usage() {
  cat <<'EOF'
Usage: scripts/auto_pr.sh [options]

Options:
  --class <name>          Change class key for cooldown/dedupe (default: auto)
  --cooldown-hours <n>    Cooldown window (default: 24)
  --generator "<cmd>"     Optional generator command (repeatable)
  --base <branch>         Base branch for PR (default: main)
  --title "<text>"        PR title override
  --body-file <path>      PR body override file
  --auto-merge-docs-only  Allow squash auto-merge only for docs-only tier
  --skip-preflight        Skip preflight commands (not recommended)
  --state-file <path>     Cooldown state file path
  --force                 Bypass cooldown and dedupe checks
  --dry-run               Print decisions only
  -h, --help              Show help

Safe merge tiers:
  - docs-only: eligible for auto-merge only with --auto-merge-docs-only
  - research/_local/scripts: PR-only (manual review)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --class)
      CHANGE_CLASS="${2:-}"
      shift 2
      ;;
    --cooldown-hours)
      COOLDOWN_HOURS="${2:-}"
      shift 2
      ;;
    --generator)
      GENERATOR_CMDS+=("${2:-}")
      shift 2
      ;;
    --base)
      BASE_BRANCH="${2:-}"
      shift 2
      ;;
    --title)
      PR_TITLE="${2:-}"
      shift 2
      ;;
    --body-file)
      PR_BODY_FILE="${2:-}"
      shift 2
      ;;
    --auto-merge-docs-only)
      AUTO_MERGE_DOCS_ONLY=1
      shift
      ;;
    --skip-preflight)
      SKIP_PREFLIGHT=1
      shift
      ;;
    --state-file)
      STATE_FILE="${2:-}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "$COOLDOWN_HOURS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --cooldown-hours must be an integer" >&2
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI is required (brew install gh)" >&2
  exit 4
fi

if [[ "$DRY_RUN" -eq 0 ]]; then
  git fetch origin "$BASE_BRANCH"
  if [[ "$(git rev-parse --abbrev-ref HEAD)" == "$BASE_BRANCH" ]]; then
    git pull --ff-only origin "$BASE_BRANCH"
  fi
fi

for cmd in "${GENERATOR_CMDS[@]}"; do
  [[ -z "$cmd" ]] && continue
  echo "[auto_pr] generator: $cmd"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    bash -lc "$cmd"
  fi
done

scripts/check_allowlist_changes.sh --worktree
CHANGED_FILES="$(scripts/check_allowlist_changes.sh --worktree --list-changed || true)"
if [[ -z "${CHANGED_FILES// }" ]]; then
  echo "[auto_pr] no allowlisted changes detected; exit 0"
  exit 0
fi

infer_tier() {
  local changed="$1"
  local docs=1
  local has_research_or_local=0
  local has_scripts=0
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    case "$f" in
      docs/*) ;;
      research/*|_local/*)
        docs=0
        has_research_or_local=1
        ;;
      scripts/auto_pr.sh|scripts/check_allowlist_changes.sh)
        docs=0
        has_scripts=1
        ;;
      *)
        docs=0
        ;;
    esac
  done <<< "$changed"

  if [[ "$docs" -eq 1 ]]; then
    echo "docs-only"
  elif [[ "$has_research_or_local" -eq 1 && "$has_scripts" -eq 0 ]]; then
    echo "research-local"
  elif [[ "$has_scripts" -eq 1 ]]; then
    echo "ops-tooling"
  else
    echo "mixed-safe"
  fi
}

TIER="$(infer_tier "$CHANGED_FILES")"
if [[ "$CHANGE_CLASS" == "auto" ]]; then
  CHANGE_CLASS="$TIER"
fi

if [[ -z "$PR_TITLE" ]]; then
  case "$TIER" in
    docs-only)
      PR_TITLE="[Auto-PR][docs] docs updates"
      ;;
    research-local)
      PR_TITLE="[Auto-PR][research] research/_local updates"
      ;;
    ops-tooling)
      PR_TITLE="[Auto-PR][ops] auto-pr tooling updates"
      ;;
    *)
      PR_TITLE="[Auto-PR] safe-tier updates"
      ;;
  esac
fi

FINGERPRINT="$(
  {
    printf '%s\n' "$CHANGED_FILES"
    git diff -- docs research _local scripts/auto_pr.sh scripts/check_allowlist_changes.sh || true
    git diff --cached -- docs research _local scripts/auto_pr.sh scripts/check_allowlist_changes.sh || true
  } | shasum -a 256 | awk '{print $1}'
)"
NOW_EPOCH="$(date +%s)"

if [[ -f "$STATE_FILE" && "$FORCE" -eq 0 ]]; then
  CHECK="$(python3 - "$STATE_FILE" "$CHANGE_CLASS" "$FINGERPRINT" "$COOLDOWN_HOURS" "$NOW_EPOCH" <<'PY'
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
klass = sys.argv[2]
fingerprint = sys.argv[3]
cooldown_h = int(sys.argv[4])
now = int(sys.argv[5])

try:
    data = json.loads(state_path.read_text(encoding="utf-8"))
except Exception:
    print("ok")
    raise SystemExit(0)

classes = data.get("classes", {})
entry = classes.get(klass, {}) if isinstance(classes, dict) else {}
last_epoch = int(entry.get("last_pr_created_epoch", 0) or 0)
last_fp = str(entry.get("last_fingerprint", ""))

if last_fp and last_fp == fingerprint:
    print("dedupe")
elif last_epoch > 0 and (now - last_epoch) < cooldown_h * 3600:
    print("cooldown")
else:
    print("ok")
PY
)"
  if [[ "$CHECK" == "dedupe" ]]; then
    echo "[auto_pr] dedupe hit for class '$CHANGE_CLASS'; skip."
    exit 0
  fi
  if [[ "$CHECK" == "cooldown" ]]; then
    echo "[auto_pr] cooldown active for class '$CHANGE_CLASS'; skip."
    exit 0
  fi
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[auto_pr][dry-run] tier=$TIER class=$CHANGE_CLASS"
  echo "[auto_pr][dry-run] title=$PR_TITLE"
  echo "[auto_pr][dry-run] changed files:"
  printf '%s\n' "$CHANGED_FILES"
  exit 0
fi

if git status --porcelain | rg '^.. data/' >/dev/null; then
  echo "[auto_pr] ERROR: data/** staged artifacts detected before commit" >&2
  exit 1
fi

PRECHECK_LOG="$(mktemp)"
{
  echo "# Preflight transcript ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
} > "$PRECHECK_LOG"

run_and_log() {
  local cmd="$1"
  echo "\$ $cmd" >> "$PRECHECK_LOG"
  set +e
  bash -lc "$cmd" >> "$PRECHECK_LOG" 2>&1
  local rc=$?
  set -e
  echo "[exit=$rc]" >> "$PRECHECK_LOG"
  return $rc
}

if [[ "$SKIP_PREFLIGHT" -eq 0 ]]; then
  run_and_log "bash scripts/install_hongstr_skills.sh --force"
  run_and_log "./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py"
  run_and_log "./.venv/bin/python -m pytest -q research/**/tests || true"
  run_and_log "git diff --name-only origin/main...HEAD | rg '^src/hongstr/' && echo 'BAD core diff' && exit 1 || true"
  run_and_log "rg -n 'subprocess|os\\.system|Popen' _local/telegram_cp/tg_cp_server.py && echo 'BAD no-exec' && exit 1 || true"
  run_and_log "git status --porcelain | rg '^.. data/' && echo 'BAD data staged' && exit 1 || true"
fi

TS="$(date -u +%Y%m%d_%H%M%S)"
BRANCH="codex/auto-pr-${CHANGE_CLASS}-${TS}"
git checkout -b "$BRANCH"

git add -A
scripts/check_allowlist_changes.sh --staged
if git status --porcelain | rg '^.. data/' >/dev/null; then
  echo "[auto_pr] ERROR: data/** staged artifacts detected after add" >&2
  exit 1
fi

if git diff --cached --quiet; then
  echo "[auto_pr] nothing staged; exit 0"
  exit 0
fi

git commit -m "ops(auto_pr): ${CHANGE_CLASS} updates"
git push -u origin "$BRANCH"

if [[ -z "$PR_BODY_FILE" ]]; then
  PR_BODY_FILE="$(mktemp)"
  {
    echo "## Summary"
    echo "- Automated safe-tier update via \`scripts/auto_pr.sh\`"
    echo "- Tier: \`$TIER\`"
    echo "- Class: \`$CHANGE_CLASS\`"
    echo ""
    echo "## Safety Statement"
    echo "- Allowlist-enforced paths only: docs/research/_local (+ auto_pr tooling scripts)."
    echo "- \`src/hongstr/**\` core semantics are blocked."
    echo "- \`data/**\` artifacts are blocked from commit."
    echo "- tg_cp no-exec invariant preserved."
    echo ""
    echo "## Rollback"
    echo "- \`git revert <merge_commit_sha>\`"
    echo ""
    echo "## Preflight Transcript"
    echo '```text'
    cat "$PRECHECK_LOG"
    echo '```'
  } > "$PR_BODY_FILE"
fi

PR_URL="$(gh pr create --base "$BASE_BRANCH" --head "$BRANCH" --title "$PR_TITLE" --body-file "$PR_BODY_FILE")"
echo "[auto_pr] PR created: $PR_URL"

mkdir -p "$(dirname "$STATE_FILE")"
python3 - "$STATE_FILE" "$CHANGE_CLASS" "$FINGERPRINT" "$NOW_EPOCH" "$PR_URL" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

state_path = Path(sys.argv[1])
klass = sys.argv[2]
fp = sys.argv[3]
epoch = int(sys.argv[4])
pr_url = sys.argv[5]

state = {}
if state_path.exists():
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        state = {}
if not isinstance(state, dict):
    state = {}

classes = state.get("classes")
if not isinstance(classes, dict):
    classes = {}
    state["classes"] = classes

classes[klass] = {
    "last_pr_created_epoch": epoch,
    "last_pr_created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "last_fingerprint": fp,
    "last_pr_url": pr_url,
}
state["updated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
PY

if [[ "$AUTO_MERGE_DOCS_ONLY" -eq 1 && "$TIER" == "docs-only" ]]; then
  echo "[auto_pr] docs-only tier with auto-merge enabled -> watching checks"
  gh pr checks "$PR_URL" --watch
  gh pr merge "$PR_URL" --squash --delete-branch
  git checkout "$BASE_BRANCH"
  git pull --ff-only origin "$BASE_BRANCH"
else
  echo "[auto_pr] PR opened without auto-merge (tier policy)."
fi
