#!/usr/bin/env bash
# HONGSTR Worker Pack Bootstrap (macOS-only, idempotent)
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash scripts/worker_pack_bootstrap.sh [options]

Options:
  --repo-url <url>         Git URL (default: origin URL from this repo)
  --repo-dir <path>        Target clone path (default: ~/Projects/HONGSTR)
  --branch <name>          Branch to track (default: main)
  --skip-brew              Skip Homebrew dependency install step
  --skip-smoke             Skip smoke tests
  -h, --help               Show this help

Environment defaults written to .env.worker:
  HONGSTR_WORKER_RUN_MINUTES=40
  HONGSTR_WORKER_SLEEP_MINUTES=10
USAGE
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[worker_bootstrap] macOS only. Detected: $(uname -s)" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_REPO_URL="${HONGSTR_WORKER_REPO_URL:-$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || echo "git@github.com:HCH725/HONGSTR.git")}"
REPO_URL="$DEFAULT_REPO_URL"
REPO_DIR="${HONGSTR_WORKER_REPO_DIR:-$HOME/Projects/HONGSTR}"
TARGET_BRANCH="${HONGSTR_WORKER_BRANCH:-main}"
SKIP_BREW=0
SKIP_SMOKE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)
      REPO_URL="$2"
      shift 2
      ;;
    --repo-dir)
      REPO_DIR="$2"
      shift 2
      ;;
    --branch)
      TARGET_BRANCH="$2"
      shift 2
      ;;
    --skip-brew)
      SKIP_BREW=1
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE=1
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

echo "== HONGSTR Worker Pack Bootstrap =="
echo "[worker_bootstrap] repo_url=${REPO_URL}"
echo "[worker_bootstrap] repo_dir=${REPO_DIR}"
echo "[worker_bootstrap] branch=${TARGET_BRANCH}"

if ! xcode-select -p >/dev/null 2>&1; then
  echo "[worker_bootstrap] Xcode Command Line Tools missing. Run: xcode-select --install" >&2
  exit 1
fi

if [[ "$SKIP_BREW" -eq 0 ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "[worker_bootstrap] Homebrew not found. Install from https://brew.sh then re-run." >&2
    exit 1
  fi
  BREW_PACKAGES=(git jq rsync python@3.11 tailscale)
  for pkg in "${BREW_PACKAGES[@]}"; do
    if brew list --versions "$pkg" >/dev/null 2>&1; then
      echo "[worker_bootstrap] brew package already installed: $pkg"
    else
      echo "[worker_bootstrap] installing brew package: $pkg"
      brew install "$pkg"
    fi
  done
else
  echo "[worker_bootstrap] skip brew packages"
fi

mkdir -p "$(dirname "$REPO_DIR")"
if [[ ! -d "$REPO_DIR/.git" ]]; then
  if [[ -e "$REPO_DIR" && ! -d "$REPO_DIR/.git" ]]; then
    echo "[worker_bootstrap] Target exists but is not a git repo: $REPO_DIR" >&2
    exit 1
  fi
  echo "[worker_bootstrap] cloning repository"
  git clone "$REPO_URL" "$REPO_DIR"
fi

cd "$REPO_DIR"
git fetch origin "$TARGET_BRANCH"
git checkout "$TARGET_BRANCH"
git pull --ff-only origin "$TARGET_BRANCH"

if [[ ! -d ".venv" ]]; then
  echo "[worker_bootstrap] creating .venv"
  python3 -m venv .venv
fi

./.venv/bin/python -m pip install --upgrade pip wheel
if [[ -f "requirements.txt" ]]; then
  ./.venv/bin/python -m pip install -r requirements.txt
else
  ./.venv/bin/python -m pip install pytest
fi

bash scripts/install_hongstr_skills.sh --force

ENV_FILE=".env.worker"
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<'ENVEOF'
# Worker Pack runtime defaults (macOS worker)
HONGSTR_WORKER_RUN_MINUTES=40
HONGSTR_WORKER_SLEEP_MINUTES=10
HONGSTR_WORKER_BETWEEN_RUNS_SECONDS=5
HONGSTR_WORKER_STATE_DIR=_local/worker_state
HONGSTR_WORKER_MAIN_BRANCH=main
HONGSTR_WORKER_RESEARCH_DRY_RUN=0
HONGSTR_WORKER_BACKTEST_SYMBOLS="BTCUSDT ETHUSDT BNBUSDT"
HONGSTR_WORKER_BACKTEST_TIMEFRAMES="1h,4h"
HONGSTR_WORKER_BACKTEST_START="2020-01-01"
HONGSTR_WORKER_BACKTEST_END="now"

# Optional pull-model metadata for ops reference.
# Main host can pull these worker JSONs via rsync over Tailscale/SSH.
HONGSTR_WORKER_SSH_HOST=""
HONGSTR_WORKER_SSH_USER=""
HONGSTR_WORKER_REMOTE_STATE_DIR=""
ENVEOF
  echo "[worker_bootstrap] created $ENV_FILE template"
else
  echo "[worker_bootstrap] $ENV_FILE exists; keep current values"
fi

if [[ "$SKIP_SMOKE" -eq 0 ]]; then
  echo "[worker_bootstrap] running smoke tests"
  ./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
  ./.venv/bin/python -m pytest -q research/loop/tests
else
  echo "[worker_bootstrap] skip smoke tests"
fi

echo "== Bootstrap Complete =="
echo "Next:"
echo "  1) edit $REPO_DIR/.env.worker"
echo "  2) run: bash scripts/worker_run_research.sh"
echo "  3) run: bash scripts/worker_run_backtests.sh"
