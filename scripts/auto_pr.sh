#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BASE_BRANCH="main"
COOLDOWN_HOURS="${AUTO_PR_COOLDOWN_HOURS:-24}"
ALLOW_DOCS_AUTOMERGE=0
RUN_PREFLIGHT=1
DRAFT_MODE=0
NAMED_GENERATORS=()

usage() {
  cat <<'EOF'
Usage: bash scripts/auto_pr.sh [options]

Options:
  --base <branch>              Base branch to sync and open PR against (default: main)
  --cooldown-hours <hours>     Cooldown window for same change class (default: 24)
  --allow-docs-automerge       Allow docs-only PR auto-merge (default: off)
  --generator <name>           Run built-in generator (repeatable)
  --skip-preflight             Skip preflight checks
  --draft                      Create draft PR
  -h, --help                   Show this help

Environment:
  AUTO_PR_GENERATORS           Semicolon-separated generator commands
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
    --generator)
      NAMED_GENERATORS+=("$2")
      shift 2
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

if [[ -n "$(git status --porcelain)" ]]; then
  echo "[auto_pr] Working tree is dirty; aborting." >&2
  git status --short
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

resolve_named_generator() {
  local name="$1"
  case "$name" in
    regime_thresholds_calibration)
      echo "bash scripts/calibrate_regime_thresholds.sh --pr-mode"
      ;;
    *)
      return 1
      ;;
  esac
}

if [[ "${#NAMED_GENERATORS[@]}" -gt 0 ]]; then
  echo "[auto_pr] Running named generators ..."
  for gen in "${NAMED_GENERATORS[@]}"; do
    if ! cmd="$(resolve_named_generator "$gen")"; then
      echo "[auto_pr] Unknown generator name: $gen" >&2
      exit 2
    fi
    run_generator_cmd "$cmd"
  done
fi

if [[ -n "${AUTO_PR_GENERATORS:-}" ]]; then
  echo "[auto_pr] Running generators ..."
  IFS=';' read -r -a generators <<< "$AUTO_PR_GENERATORS"
  for cmd in "${generators[@]}"; do
    run_generator_cmd "$cmd"
  done
fi

mapfile -t CHANGED < <(
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
trap 'rm -f "$ALLOW_JSON" "$CLASS_JSON" "$PREFLIGHT_TXT" "$BODY_FILE"' EXIT

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
  echo "[auto_pr] Skip due to cooldown/dedupe: $SKIP_REASON"
  exit 0
fi

sanitize_kind=$(echo "$KIND" | tr -cs 'a-zA-Z0-9' '-')
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
cat > "$BODY_FILE" <<MD
## Summary
$TITLE

## Changed Paths
$(printf -- '- `%s`\n' "${CHANGED[@]}")

## Safety Statement
- Allowlist guard enforced (`docs/**`, `_local/**`, `research/**`, `scripts/**`).
- `src/hongstr/**` is blocked.
- `data/**` artifacts are not committed.
- `report_only` workflow is preserved.

## Rollback
\`\`\`bash
git revert <merge_commit_sha>
\`\`\`

## Preflight Transcript
\`\`\`bash
$(cat "$PREFLIGHT_TXT")
\`\`\`
MD

PR_ARGS=(--base "$BASE_BRANCH" --head "$BRANCH" --title "[codex] $TITLE" --body-file "$BODY_FILE")
if [[ "$DRAFT_MODE" -eq 1 ]]; then
  PR_ARGS=(--draft "${PR_ARGS[@]}")
fi

PR_URL=$(GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create "${PR_ARGS[@]}")
echo "[auto_pr] PR created: $PR_URL"

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
