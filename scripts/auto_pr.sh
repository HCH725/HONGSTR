#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BASE_BRANCH="${BASE_BRANCH:-main}"
AUTO_PR_CLASS="${AUTO_PR_CLASS:-auto}"
COOLDOWN_HOURS="${COOLDOWN_HOURS:-24}"
AUTO_MERGE="${AUTO_MERGE:-0}"   # default: open PR only
STATE_FILE="${AUTO_PR_STATE_FILE:-_local/state/auto_pr_state.json}"
PR_TITLE="${PR_TITLE:-}"
PR_BODY_FILE="${PR_BODY_FILE:-}"
DRY_RUN=0
FORCE=0

GENERATOR_CMDS=()

usage() {
  cat <<'EOF'
Usage: scripts/auto_pr.sh [options]

Options:
  --class <name>            PR class key for cooldown/dedupe (default: auto)
  --cooldown-hours <n>      Cooldown window per class (default: 24)
  --generator "<cmd>"       Optional generator command (repeatable)
  --base <branch>           Base branch (default: main)
  --title "<text>"          Override PR title
  --body-file <path>        Use PR body from file
  --auto-merge              Enable squash merge after checks pass
  --no-auto-merge           Disable auto-merge (default)
  --state-file <path>       Cooldown state file (default: _local/state/auto_pr_state.json)
  --force                   Ignore cooldown and proceed
  --dry-run                 Print actions without mutating git/GitHub
  -h, --help                Show help

Guardrails:
  - allowlist must pass via scripts/check_allowlist_changes.sh
  - data/** cannot be staged
  - default behavior opens PR only (no merge)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --class)
      AUTO_PR_CLASS="${2:-}"
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
    --auto-merge)
      AUTO_MERGE=1
      shift
      ;;
    --no-auto-merge)
      AUTO_MERGE=0
      shift
      ;;
    --state-file)
      STATE_FILE="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --force)
      FORCE=1
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

if [[ "$DRY_RUN" -eq 0 ]]; then
  git checkout "$BASE_BRANCH"
  git pull --ff-only origin "$BASE_BRANCH"
fi

if [[ "${#GENERATOR_CMDS[@]}" -gt 0 ]]; then
  for cmd in "${GENERATOR_CMDS[@]}"; do
    [[ -z "$cmd" ]] && continue
    echo "[auto_pr] generator: $cmd"
    if [[ "$DRY_RUN" -eq 0 ]]; then
      bash -lc "$cmd"
    fi
  done
fi

if [[ "$DRY_RUN" -eq 0 ]]; then
  scripts/check_allowlist_changes.sh --worktree
fi

CHANGED_FILES="$(scripts/check_allowlist_changes.sh --worktree --list-changed || true)"
if [[ -z "${CHANGED_FILES// }" ]]; then
  echo "[auto_pr] no allowlisted changes; exit 0"
  exit 0
fi

if [[ "$DRY_RUN" -eq 0 ]]; then
  if git status --porcelain | rg '^.. data/' >/dev/null; then
    echo "[auto_pr] ERROR: staged data/** artifacts detected" >&2
    exit 1
  fi
fi

CHANGE_FINGERPRINT="$(printf "%s\n" "$CHANGED_FILES" | shasum -a 256 | awk '{print $1}')"
NOW_EPOCH="$(date +%s)"

COOLDOWN_ACTIVE=0
if [[ -f "$STATE_FILE" && "$FORCE" -eq 0 ]]; then
  COOLDOWN_ACTIVE="$(python3 - "$STATE_FILE" "$AUTO_PR_CLASS" "$COOLDOWN_HOURS" "$NOW_EPOCH" <<'PY'
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
klass = sys.argv[2]
cooldown_h = int(sys.argv[3])
now_epoch = int(sys.argv[4])

try:
    data = json.loads(state_path.read_text(encoding="utf-8"))
except Exception:
    print(0)
    raise SystemExit(0)

classes = data.get("classes", {})
row = classes.get(klass, {}) if isinstance(classes, dict) else {}
last_epoch = int(row.get("last_pr_created_epoch", 0) or 0)
if last_epoch <= 0:
    print(0)
else:
    print(1 if (now_epoch - last_epoch) < cooldown_h * 3600 else 0)
PY
)"
fi

if [[ "$COOLDOWN_ACTIVE" == "1" ]]; then
  echo "[auto_pr] cooldown active for class '$AUTO_PR_CLASS' within ${COOLDOWN_HOURS}h; skip."
  exit 0
fi

infer_class() {
  local changed="$1"
  local has_docs=0
  local has_skills=0
  local has_research=0
  local has_scripts=0
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    case "$f" in
      docs/*) has_docs=1 ;;
      _local/telegram_cp/*|docs/ops_skills_cmds.md) has_skills=1 ;;
      research/*) has_research=1 ;;
      scripts/*) has_scripts=1 ;;
    esac
  done <<< "$changed"

  if [[ "$has_skills" -eq 1 ]]; then
    echo "skills-docs"
    return
  fi
  if [[ "$has_research" -eq 1 || "$has_scripts" -eq 1 ]]; then
    echo "ops-audit"
    return
  fi
  if [[ "$has_docs" -eq 1 ]]; then
    echo "docs-only"
    return
  fi
  echo "auto"
}

CHANGE_CLASS="$(infer_class "$CHANGED_FILES")"
if [[ "$AUTO_PR_CLASS" == "auto" ]]; then
  AUTO_PR_CLASS="$CHANGE_CLASS"
fi

if [[ -z "$PR_TITLE" ]]; then
  case "$AUTO_PR_CLASS" in
    docs-only) PR_TITLE="[Auto-PR][docs] docs updates" ;;
    skills-docs) PR_TITLE="[Auto-PR][skills-docs] skill schema/help alignment" ;;
    ops-audit) PR_TITLE="[Auto-PR][ops-audit] governance and automation updates" ;;
    *) PR_TITLE="[Auto-PR] automated allowlisted updates" ;;
  esac
fi

TS="$(date -u +%Y%m%d_%H%M%S)"
BRANCH_NAME="codex/auto-pr-${AUTO_PR_CLASS}-${TS}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[auto_pr][dry-run] base=$BASE_BRANCH class=$AUTO_PR_CLASS"
  echo "[auto_pr][dry-run] branch=$BRANCH_NAME"
  echo "[auto_pr][dry-run] title=$PR_TITLE"
  echo "[auto_pr][dry-run] changed:"
  printf "%s\n" "$CHANGED_FILES"
  exit 0
fi

git checkout -b "$BRANCH_NAME"
git add -A

scripts/check_allowlist_changes.sh --staged

if git status --porcelain | rg '^.. data/' >/dev/null; then
  echo "[auto_pr] ERROR: staged data/** artifacts detected after git add -A" >&2
  exit 1
fi

if git diff --cached --quiet; then
  echo "[auto_pr] no staged changes after allowlist filter; exit 0"
  git checkout "$BASE_BRANCH"
  exit 0
fi

git commit -m "chore(auto-pr): ${AUTO_PR_CLASS} updates"
git push -u origin "$BRANCH_NAME"

if [[ -z "$PR_BODY_FILE" ]]; then
  TMP_BODY="$(mktemp)"
  {
    echo "## Summary"
    echo "- Automated allowlisted updates generated by \`scripts/auto_pr.sh\`"
    echo "- Change class: \`${AUTO_PR_CLASS}\`"
    echo ""
    echo "## Safety Statement"
    echo "- Only allowlisted paths are included (docs/_local/research/scripts non-prod)."
    echo "- No \`src/hongstr/**\` core semantics changes."
    echo "- No \`data/**\` artifacts committed."
    echo ""
    echo "## Changed Files"
    echo '```'
    printf "%s\n" "$CHANGED_FILES"
    echo '```'
    echo ""
    echo "## Rollback"
    echo "- \`git revert <merge_commit_sha>\`"
  } > "$TMP_BODY"
  PR_BODY_FILE="$TMP_BODY"
fi

PR_URL="$(gh pr create --base "$BASE_BRANCH" --head "$BRANCH_NAME" --title "$PR_TITLE" --body-file "$PR_BODY_FILE")"
echo "[auto_pr] PR created: $PR_URL"

mkdir -p "$(dirname "$STATE_FILE")"
python3 - "$STATE_FILE" "$AUTO_PR_CLASS" "$NOW_EPOCH" "$CHANGE_FINGERPRINT" "$PR_URL" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

state_path = Path(sys.argv[1])
klass = sys.argv[2]
epoch = int(sys.argv[3])
fingerprint = sys.argv[4]
pr_url = sys.argv[5]

data = {}
if state_path.exists():
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        data = {}

if not isinstance(data, dict):
    data = {}

classes = data.get("classes")
if not isinstance(classes, dict):
    classes = {}
    data["classes"] = classes

classes[klass] = {
    "last_pr_created_epoch": epoch,
    "last_pr_created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "last_fingerprint": fingerprint,
    "last_pr_url": pr_url,
}
data["updated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY

if [[ "$AUTO_MERGE" -eq 1 ]]; then
  echo "[auto_pr] auto-merge enabled; waiting checks..."
  gh pr checks "$PR_URL" --watch
  gh pr merge "$PR_URL" --squash --delete-branch
  git checkout "$BASE_BRANCH"
  git pull --ff-only origin "$BASE_BRANCH"
else
  echo "[auto_pr] auto-merge disabled (default). PR left open."
fi
