#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p reports logs

STRICT=0
USER_RUN_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT=1
      shift
      ;;
    --run_dir)
      USER_RUN_DIR="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  echo "No python interpreter found. Install python and run scripts/bootstrap_dev_env.sh."
  exit 2
fi

TS_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
TS_FILE="$(date -u +"%Y%m%d_%H%M%S")"
GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
LOG_PATH="$ROOT_DIR/logs/gate_all_${TS_FILE}.log"
REPORT_PATH="$ROOT_DIR/reports/gate_latest.md"
RECONCILE_PATH="$ROOT_DIR/reports/reconcile_latest.json"
touch "$LOG_PATH"

OVERALL_STATUS="PASS"
EXIT_CODE=0
WARN_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
STOP_REASON=""
SELECTION_PATH="N/A"
LATEST_RUN_DIR=""
LAST_OUTPUT=""
EXTERNAL_EVENTS=()
WARN_REMEDIATIONS=()
ENV_PYTHON_VERSION="NOT_FOUND"
ENV_PYTEST_VERSION="NOT_FOUND"
ENV_RUFF_VERSION="NOT_FOUND"
ENV_BINANCE_FUTURES_TESTNET="0"
ENV_BINANCE_TESTNET="0"
ENV_WF_LATEST_JSON="missing"
ENV_LATEST_RUN_DIR="NOT_FOUND"
PROTECTED_THIS_COMMIT="NO"
PROTECTED_WORKING_TREE="NO"
CHANGED_PATHS=()

STEP_NAMES=()
STEP_STATUS=()
STEP_RCS=()
STEP_REASONS=()

log() {
  echo "$1" | tee -a "$LOG_PATH"
}

append_step() {
  STEP_NAMES+=("$1")
  STEP_STATUS+=("$2")
  STEP_RCS+=("$3")
  STEP_REASONS+=("$4")
}

update_overall_for_warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  if [ "$OVERALL_STATUS" = "PASS" ]; then
    OVERALL_STATUS="WARN"
  fi
}

add_warn_remediation() {
  WARN_REMEDIATIONS+=("- $1")
}

mark_fail() {
  local rc="$1"
  local reason="$2"
  FAIL_COUNT=$((FAIL_COUNT + 1))
  OVERALL_STATUS="FAIL"
  EXIT_CODE="$rc"
  STOP_REASON="$reason"
}

mark_skip() {
  SKIP_COUNT=$((SKIP_COUNT + 1))
}

abs_path() {
  if [ -e "$1" ]; then
    echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
  else
    echo "$1"
  fi
}

artifact_line() {
  local label="$1"
  local p="$2"
  local abs
  abs="$(abs_path "$p")"
  if [ -e "$p" ]; then
    echo "- ${label}: ${abs} (present)"
  else
    echo "- ${label}: ${abs} (missing)"
  fi
}

is_external_failure() {
  local output="$1"
  local pats=(
    "ConnectionError" "Read timed out" "ConnectTimeout" "Timeout"
    "Max retries exceeded" "Temporary failure" "Name or service not known"
    "502 Bad Gateway" "503 Service Unavailable" "504 Gateway Timeout"
    "requests.exceptions"
  )
  for p in "${pats[@]}"; do
    if grep -q "$p" <<<"$output"; then
      return 0
    fi
  done
  return 1
}

run_and_capture() {
  local cmd="$1"
  LAST_OUTPUT=""
  local rc=0
  if LAST_OUTPUT=$(eval "$cmd" 2>&1); then
    rc=0
  else
    rc=$?
  fi
  if [ -n "$LAST_OUTPUT" ]; then
    echo "$LAST_OUTPUT" | tee -a "$LOG_PATH"
  fi
  return "$rc"
}

latest_run_dir() {
  "$PYTHON_BIN" - <<'PY'
from pathlib import Path

root = Path("data/backtests")
if not root.exists():
    raise SystemExit(1)
runs = [p for p in root.glob("*/*") if p.is_dir()]
if not runs:
    raise SystemExit(1)
runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
print(str(runs[0].resolve()))
PY
}

env_precheck() {
  ENV_PYTHON_VERSION="$("$PYTHON_BIN" --version 2>&1 || echo "NOT_FOUND")"
  if "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1; then
    ENV_PYTEST_VERSION="$("$PYTHON_BIN" -m pytest --version 2>&1 | head -n 1)"
  fi
  if "$PYTHON_BIN" -m ruff --version >/dev/null 2>&1; then
    ENV_RUFF_VERSION="$("$PYTHON_BIN" -m ruff --version 2>&1 | head -n 1)"
  fi

  ENV_BINANCE_FUTURES_TESTNET="${BINANCE_FUTURES_TESTNET:-0}"
  ENV_BINANCE_TESTNET="${BINANCE_TESTNET:-0}"

  if [ -f "$ROOT_DIR/reports/walkforward_latest.json" ]; then
    ENV_WF_LATEST_JSON="present"
  fi

  if ENV_LATEST_RUN_DIR="$(latest_run_dir 2>/dev/null)"; then
    :
  else
    ENV_LATEST_RUN_DIR="NOT_FOUND"
  fi

  detect_protected_touches
  collect_changed_paths

  log "=== ENV PRECHECK ==="
  log "python --version: ${ENV_PYTHON_VERSION}"
  log "python -m pytest --version: ${ENV_PYTEST_VERSION}"
  log "python -m ruff --version: ${ENV_RUFF_VERSION}"
  if [ "$ENV_BINANCE_FUTURES_TESTNET" = "1" ]; then
    log "BINANCE_FUTURES_TESTNET=1"
  else
    log "BINANCE_FUTURES_TESTNET!=1 (${ENV_BINANCE_FUTURES_TESTNET})"
  fi
  if [ "$ENV_BINANCE_TESTNET" = "1" ]; then
    log "BINANCE_TESTNET=1"
  else
    log "BINANCE_TESTNET!=1 (${ENV_BINANCE_TESTNET})"
  fi
  log "reports/walkforward_latest.json: ${ENV_WF_LATEST_JSON}"
  log "data/backtests latest run_dir: ${ENV_LATEST_RUN_DIR}"
  log "Protected touched THIS commit?: ${PROTECTED_THIS_COMMIT}"
  log "Protected changed in working tree?: ${PROTECTED_WORKING_TREE}"
}

detect_protected_touches() {
  local commit_files
  commit_files="$(git show --name-only --pretty='' HEAD 2>/dev/null || true)"
  if grep -Eq '^src/hongstr/backtest/|^src/hongstr/execution/' <<<"$commit_files"; then
    PROTECTED_THIS_COMMIT="YES"
  else
    PROTECTED_THIS_COMMIT="NO"
  fi

  local line
  local path
  PROTECTED_WORKING_TREE="NO"
  while IFS= read -r line; do
    path="${line:3}"
    if [[ "$path" == *" -> "* ]]; then
      path="${path##* -> }"
    fi
    if [[ "$path" == src/hongstr/backtest/* || "$path" == src/hongstr/execution/* ]]; then
      PROTECTED_WORKING_TREE="YES"
      break
    fi
  done < <(git status --porcelain 2>/dev/null || true)
}

parse_smoke_field() {
  local line="$1"
  local key="$2"
  sed -n "s/.*${key}=\\([^ ]*\\).*/\\1/p" <<<"$line"
}

collect_changed_paths() {
  local out
  out="$(git diff --name-only -- scripts tests docs/handoff configs pyproject.toml 2>/dev/null || true)"
  CHANGED_PATHS=()
  if [ -z "$out" ]; then
    return
  fi
  while IFS= read -r p; do
    [ -n "$p" ] && CHANGED_PATHS+=("$p")
  done <<<"$out"
}

write_reconcile_json() {
  local status="$1"
  local note="$2"
  cat > "$RECONCILE_PATH" <<EOF
{
  "generated_at": "${TS_UTC}",
  "status": "${status}",
  "note": "${note}",
  "orders_report": "$(abs_path "$ROOT_DIR/reports/orders_latest.json")"
}
EOF
}

write_report() {
  {
    echo "# Gate All Report"
    echo ""
    echo "- Timestamp (UTC): ${TS_UTC}"
    echo "- Git Commit: ${GIT_COMMIT}"
    echo "- Python: ${PYTHON_BIN}"
    echo "- Strict Mode: ${STRICT}"
    echo "- Overall: ${OVERALL_STATUS}"
    echo "- Exit Code: ${EXIT_CODE}"
    echo "- Stop Reason: ${STOP_REASON:-none}"
    echo "- Log: $(abs_path "$LOG_PATH")"
    echo ""
    echo "## Env Precheck"
    echo "- python --version: ${ENV_PYTHON_VERSION}"
    echo "- python -m pytest --version: ${ENV_PYTEST_VERSION}"
    echo "- python -m ruff --version: ${ENV_RUFF_VERSION}"
    echo "- BINANCE_FUTURES_TESTNET: ${ENV_BINANCE_FUTURES_TESTNET}"
    echo "- BINANCE_TESTNET: ${ENV_BINANCE_TESTNET}"
    echo "- reports/walkforward_latest.json: ${ENV_WF_LATEST_JSON}"
    echo "- data/backtests latest run_dir: ${ENV_LATEST_RUN_DIR}"
    echo ""
    echo "## Protected Touch Status"
    echo "- Protected touched THIS commit?: ${PROTECTED_THIS_COMMIT}"
    echo "- Protected changed in working tree?: ${PROTECTED_WORKING_TREE}"
    echo ""
    echo "## Status Summary"
    echo "- WARN count: ${WARN_COUNT}"
    echo "- FAIL count: ${FAIL_COUNT}"
    echo "- SKIP count: ${SKIP_COUNT}"
    echo ""
    echo "## Step Results"
    local i
    for ((i = 0; i < ${#STEP_NAMES[@]}; i++)); do
      echo "- ${STEP_NAMES[$i]}: ${STEP_STATUS[$i]} (rc=${STEP_RCS[$i]}; reason=${STEP_REASONS[$i]})"
    done
    echo ""
    if [ "${#EXTERNAL_EVENTS[@]}" -gt 0 ]; then
      echo "## External/Network Degradation"
      for ev in "${EXTERNAL_EVENTS[@]}"; do
        echo "- ${ev}"
      done
      echo ""
    fi
    if [ "${#WARN_REMEDIATIONS[@]}" -gt 0 ]; then
      echo "## Remediation"
      for item in "${WARN_REMEDIATIONS[@]}"; do
        echo "${item}"
      done
      echo ""
    fi
    echo "## Key Artifacts"
    artifact_line "reports/walkforward_latest.json" "$ROOT_DIR/reports/walkforward_latest.json"
    artifact_line "reports/walkforward_latest.md" "$ROOT_DIR/reports/walkforward_latest.md"
    echo "- selection.json used: ${SELECTION_PATH}"
    artifact_line "reports/action_items_latest.json" "$ROOT_DIR/reports/action_items_latest.json"
    artifact_line "reports/action_items_latest.md" "$ROOT_DIR/reports/action_items_latest.md"
    artifact_line "reports/orders_latest.json" "$ROOT_DIR/reports/orders_latest.json"
    artifact_line "reports/orders_latest.md" "$ROOT_DIR/reports/orders_latest.md"
    artifact_line "reports/reconcile_latest.json" "$RECONCILE_PATH"
    if [ -n "$LATEST_RUN_DIR" ]; then
      echo "- resolved run_dir: $(abs_path "$LATEST_RUN_DIR")"
    fi
    echo ""
    echo "## Command Examples"
    echo "- bash scripts/bootstrap_dev_env.sh"
    echo "- bash scripts/gate_all.sh"
    echo "- bash scripts/gate_all.sh --strict"
  } > "$REPORT_PATH"
}

scan_secret_leaks() {
  local leak=0
  local candidates=("$LOG_PATH" "$REPORT_PATH")
  local key="${BINANCE_API_KEY:-}"
  local secret="${BINANCE_API_SECRET:-}"

  if [ -n "$key" ]; then
    for f in "${candidates[@]}"; do
      if [ -f "$f" ] && grep -Fq "$key" "$f"; then
        leak=1
      fi
    done
  fi
  if [ -n "$secret" ]; then
    for f in "${candidates[@]}"; do
      if [ -f "$f" ] && grep -Fq "$secret" "$f"; then
        leak=1
      fi
    done
  fi
  if [ "$leak" -eq 1 ]; then
    return 0
  fi
  return 1
}

stop_if_failed() {
  if [ "$OVERALL_STATUS" = "FAIL" ]; then
    write_reconcile_json "SKIPPED" "gate stopped: ${STOP_REASON}"
    write_report
    exit "$EXIT_CODE"
  fi
}

log "Starting gate_all at ${TS_UTC} (commit ${GIT_COMMIT})"
env_precheck

# Step 1: ruff precheck + lint
STEP="python -m ruff check ."
log ""
log "=== ${STEP} ==="
if "$PYTHON_BIN" -m ruff --version >/dev/null 2>&1; then
  log "\$ $PYTHON_BIN -m ruff check . --exclude _untracked_quarantine"
  if run_and_capture "\"$PYTHON_BIN\" -m ruff check . --exclude _untracked_quarantine"; then
    append_step "$STEP" "PASS" 0 "ok"
  else
    STEP_CMD_RC=$?
    append_step "$STEP" "WARN" "$STEP_CMD_RC" "lint debt (pre-existing)"
    update_overall_for_warn
    add_warn_remediation "ruff debt (pre-existing): python3 -m ruff check . --statistics"
    add_warn_remediation "ruff focused (changed files): python3 -m ruff check <changed_paths>"
    add_warn_remediation "ruff install: python3 -m pip install -e \".[dev]\" || python3 -m pip install ruff"
  fi
else
  log "Missing module: ruff. Install with: pip install -e \".[dev]\""
  if [ "$STRICT" = "1" ]; then
    append_step "$STEP" "FATAL" 1 "missing module; install with pip install -e \".[dev]\""
    mark_fail 1 "ruff module missing (strict)"
  else
    append_step "$STEP" "WARN" 1 "missing module; install with pip install -e \".[dev]\""
    update_overall_for_warn
    add_warn_remediation "ruff missing: python3 -m pip install -e \".[dev]\" || python3 -m pip install ruff"
  fi
fi
stop_if_failed

STEP="python -m ruff check <changed_paths>"
log ""
log "=== ${STEP} ==="
if [ "${#CHANGED_PATHS[@]}" -eq 0 ]; then
  append_step "$STEP" "SKIP" 0 "no changed paths under scripts/tests/docs/handoff/configs/pyproject.toml"
  mark_skip
else
  if ! "$PYTHON_BIN" -m ruff --version >/dev/null 2>&1; then
    append_step "$STEP" "SKIP" 1 "ruff module missing; cannot run changed-path lint"
    mark_skip
    add_warn_remediation "ruff missing: python3 -m pip install -e \".[dev]\" || python3 -m pip install ruff"
  else
    RUFF_CHANGED_CMD="\"$PYTHON_BIN\" -m ruff check"
    for p in "${CHANGED_PATHS[@]}"; do
      RUFF_CHANGED_CMD="${RUFF_CHANGED_CMD} \"$p\""
    done
    log "\$ ${RUFF_CHANGED_CMD}"
    if run_and_capture "${RUFF_CHANGED_CMD}"; then
      append_step "$STEP" "PASS" 0 "ok"
    else
      STEP_CMD_RC=$?
      append_step "$STEP" "WARN" "$STEP_CMD_RC" "lint debt on changed paths"
      update_overall_for_warn
      add_warn_remediation "ruff changed paths detail: python3 -m ruff check ${CHANGED_PATHS[*]}"
    fi
  fi
fi

# Step 2: pytest precheck + test
STEP="python -m pytest -q -m \"not integration\""
log ""
log "=== ${STEP} ==="
if "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1; then
  log "\$ $PYTHON_BIN -m pytest -q -m \"not integration\""
  if run_and_capture "\"$PYTHON_BIN\" -m pytest -q -m \"not integration\""; then
    append_step "$STEP" "PASS" 0 "ok"
  else
    STEP_CMD_RC=$?
    append_step "$STEP" "FAIL" "$STEP_CMD_RC" "tests failed"
    mark_fail "$STEP_CMD_RC" "pytest failed"
  fi
else
  log "Missing module: pytest. Install with: pip install -e \".[dev]\""
  append_step "$STEP" "FATAL" 1 "missing module; install with pip install -e \".[dev]\""
  mark_fail 1 "pytest module missing"
fi
stop_if_failed

# Step 3: smoke backtest
STEP="bash scripts/smoke_backtest.sh"
log ""
log "=== ${STEP} ==="
log "\$ bash scripts/smoke_backtest.sh"
if run_and_capture "bash scripts/smoke_backtest.sh"; then
  append_step "$STEP" "PASS" 0 "ok"
else
  STEP_CMD_RC=$?
  append_step "$STEP" "FAIL" "$STEP_CMD_RC" "smoke backtest failed"
  mark_fail "$STEP_CMD_RC" "smoke_backtest failed"
fi
stop_if_failed

# Step 4: walkforward suite
STEP="bash scripts/walkforward_suite.sh --quick --symbols BTCUSDT"
log ""
log "=== ${STEP} ==="
log "\$ bash scripts/walkforward_suite.sh --quick --symbols \"BTCUSDT\""
if run_and_capture "bash scripts/walkforward_suite.sh --quick --symbols \"BTCUSDT\""; then
  append_step "$STEP" "PASS" 0 "ok"
else
  STEP_CMD_RC=$?
  if grep -Eq "No data for|No backtest results produced\\.|Insufficient data for resampling" <<<"$LAST_OUTPUT"; then
    WF_RUN_ID_HINT="$(sed -n 's/^Run ID: \(.*\)$/\1/p' <<<"$LAST_OUTPUT" | tail -n1 | tr -d '[:space:]')"
    append_step "$STEP" "SKIP" "$STEP_CMD_RC" "QUICK_SKIPPED_INSUFFICIENT_LOCAL_DATA"
    mark_skip
    update_overall_for_warn
    if [ -n "$WF_RUN_ID_HINT" ]; then
      add_warn_remediation "walkforward quick diagnostics: inspect $ROOT_DIR/reports/walkforward/${WF_RUN_ID_HINT}/failure_diagnostics.json"
      add_warn_remediation "walkforward quick diagnostics markdown: inspect $ROOT_DIR/reports/walkforward/${WF_RUN_ID_HINT}/failure_diagnostics.md"
    fi
    add_warn_remediation "walkforward quick retry: bash scripts/walkforward_suite.sh --quick --symbols BTCUSDT"
    add_warn_remediation "walkforward local data precheck: bash scripts/smoke_backtest.sh"
  else
    append_step "$STEP" "FAIL" "$STEP_CMD_RC" "walkforward suite failed"
    mark_fail "$STEP_CMD_RC" "walkforward suite failed"
  fi
fi
stop_if_failed

# Step 5: report walkforward (uses latest suite run by default)
STEP="python3 scripts/report_walkforward.py"
log ""
log "=== ${STEP} ==="
log "\$ $PYTHON_BIN scripts/report_walkforward.py"
if run_and_capture "\"$PYTHON_BIN\" scripts/report_walkforward.py"; then
  append_step "$STEP" "PASS" 0 "ok"
  if grep -q "^LATEST_UPDATED " <<<"$LAST_OUTPUT"; then
    LATEST_JSON_PATH="$(sed -n 's/.*latest_json=\([^ ]*\).*/\1/p' <<<"$LAST_OUTPUT" | tail -n1)"
    if [ -z "$LATEST_JSON_PATH" ]; then
      LATEST_JSON_PATH="reports/walkforward_latest.json"
    fi
    append_step "walkforward latest pointer update" "PASS" 0 "latest updated -> ${LATEST_JSON_PATH}"
  elif grep -q "^WARN reason=" <<<"$LAST_OUTPUT"; then
    LATEST_REASON_CODE="$(sed -n 's/.*reason=\([^ ]*\).*/\1/p' <<<"$LAST_OUTPUT" | tail -n1)"
    RUN_DIR_HINT="$(sed -n 's/.*run_dir=\([^ ]*\).*/\1/p' <<<"$LAST_OUTPUT" | tail -n1)"
    FAILED_HINT="$(sed -n 's/.*failed_windows=\([^"]*\).*/\1/p' <<<"$LAST_OUTPUT" | tail -n1)"
    if [ -z "$RUN_DIR_HINT" ]; then
      RUN_DIR_HINT="reports/walkforward/<RUN_ID>/"
    fi
    if [ -z "$LATEST_REASON_CODE" ]; then
      LATEST_REASON_CODE="LATEST_NOT_UPDATED_STALE_RISK"
    fi
    if [ -z "$FAILED_HINT" ]; then
      FAILED_HINT="unknown"
    fi
    append_step "walkforward latest pointer update" "WARN" 0 "${LATEST_REASON_CODE} failed_windows=${FAILED_HINT}"
    update_overall_for_warn
    add_warn_remediation "walkforward latest pointer: inspect ${RUN_DIR_HINT}"
    if [ -f "${RUN_DIR_HINT}/failure_diagnostics.json" ]; then
      add_warn_remediation "walkforward failure diagnostics: inspect ${RUN_DIR_HINT}/failure_diagnostics.json and .md"
    fi
    add_warn_remediation "walkforward rerun: bash scripts/walkforward_suite.sh --quick --symbols BTCUSDT"
    add_warn_remediation "walkforward report rerender: python3 scripts/report_walkforward.py --run_id $(basename ${RUN_DIR_HINT})"
    if [ -f "$ROOT_DIR/reports/walkforward_rerun_latest.json" ]; then
      RERUN_INFO="$("$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path
p=Path("reports/walkforward_rerun_latest.json")
if not p.exists():
    raise SystemExit(1)
j=json.loads(p.read_text(encoding="utf-8"))
print(
    f"{j.get('run_mode','')}\t{j.get('completed','?')}\t{j.get('total','?')}\t{j.get('failed','?')}\t"
    f"{j.get('selected_completed', '?')}\t{j.get('selected_total', '?')}\t{j.get('selected_failed', '?')}"
)
PY
 2>/dev/null || true)"
      if [ -n "$RERUN_INFO" ]; then
        RERUN_MODE="$(awk -F'\t' '{print $1}' <<<"$RERUN_INFO")"
        RERUN_COMPLETED="$(awk -F'\t' '{print $2}' <<<"$RERUN_INFO")"
        RERUN_TOTAL="$(awk -F'\t' '{print $3}' <<<"$RERUN_INFO")"
        RERUN_FAILED="$(awk -F'\t' '{print $4}' <<<"$RERUN_INFO")"
        RERUN_SELECTED_COMPLETED="$(awk -F'\t' '{print $5}' <<<"$RERUN_INFO")"
        RERUN_SELECTED_TOTAL="$(awk -F'\t' '{print $6}' <<<"$RERUN_INFO")"
        RERUN_SELECTED_FAILED="$(awk -F'\t' '{print $7}' <<<"$RERUN_INFO")"
        if [ "$RERUN_MODE" = "RERUN" ]; then
          if [ "$RERUN_SELECTED_TOTAL" != "?" ] && [ "$RERUN_SELECTED_COMPLETED" = "$RERUN_SELECTED_TOTAL" ] && [ "$RERUN_SELECTED_FAILED" = "0" ]; then
            append_step "walkforward rerun mode status" "PASS" 0 "RERUN_OK_SELECTED_COMPLETE selected=${RERUN_SELECTED_COMPLETED}/${RERUN_SELECTED_TOTAL} full_total=${RERUN_TOTAL}; latest pointers not updated by policy"
          else
            append_step "walkforward rerun mode status" "WARN" 0 "RERUN_PARTIAL_EXPECTED selected=${RERUN_SELECTED_COMPLETED}/${RERUN_SELECTED_TOTAL} full_total=${RERUN_TOTAL} failed=${RERUN_FAILED}; latest pointers not updated by policy"
            update_overall_for_warn
          fi
        fi
      fi
      add_warn_remediation "walkforward rerun latest: inspect $ROOT_DIR/reports/walkforward_rerun_latest.json and .md"
    fi
  fi
else
  STEP_CMD_RC=$?
  append_step "$STEP" "FAIL" "$STEP_CMD_RC" "report generation failed"
  mark_fail "$STEP_CMD_RC" "report_walkforward failed"
fi
stop_if_failed

# Step 6: resolve latest run_dir
STEP="resolve latest run_dir for selection"
log ""
log "=== ${STEP} ==="
if [ -n "$USER_RUN_DIR" ]; then
  if [ -d "$USER_RUN_DIR" ]; then
    LATEST_RUN_DIR="$USER_RUN_DIR"
    append_step "$STEP" "PASS" 0 "using --run_dir"
  else
    append_step "$STEP" "FAIL" 1 "--run_dir not found: $USER_RUN_DIR"
    mark_fail 1 "provided run_dir not found"
  fi
else
  if LATEST_RUN_DIR="$(latest_run_dir)"; then
    append_step "$STEP" "PASS" 0 "resolved $(abs_path "$LATEST_RUN_DIR")"
  else
    append_step "$STEP" "SKIP" 0 "no backtest run dir found under data/backtests/**"
    mark_skip
  fi
fi
stop_if_failed

# Step 7: selection artifact
STEP="python3 scripts/generate_selection_artifact.py --run_dir <latest>"
log ""
log "=== ${STEP} ==="
if [ -z "$LATEST_RUN_DIR" ]; then
  append_step "$STEP" "SKIP" 0 "no run_dir resolved"
  mark_skip
else
  SELECTION_PATH="$(abs_path "$LATEST_RUN_DIR/selection.json")"
  log "\$ $PYTHON_BIN scripts/generate_selection_artifact.py --run_dir \"$LATEST_RUN_DIR\""
  if run_and_capture "\"$PYTHON_BIN\" scripts/generate_selection_artifact.py --run_dir \"$LATEST_RUN_DIR\""; then
    append_step "$STEP" "PASS" 0 "ok"
  else
    STEP_CMD_RC=$?
    append_step "$STEP" "FAIL" "$STEP_CMD_RC" "selection artifact generation failed"
    mark_fail "$STEP_CMD_RC" "selection artifact failed with resolved run_dir"
  fi
fi
stop_if_failed

# Step 8: action items
STEP="python3 scripts/generate_action_items.py"
log ""
log "=== ${STEP} ==="
log "\$ $PYTHON_BIN scripts/generate_action_items.py"
if run_and_capture "\"$PYTHON_BIN\" scripts/generate_action_items.py"; then
  append_step "$STEP" "PASS" 0 "ok"
else
  STEP_CMD_RC=$?
  append_step "$STEP" "FAIL" "$STEP_CMD_RC" "action items generation failed"
  mark_fail "$STEP_CMD_RC" "generate_action_items failed"
fi
stop_if_failed

# Step 9: exchange smoke test (missing key -> WARN)
STEP="python3 scripts/exchange_smoke_test.py --debug_signing"
log ""
log "=== ${STEP} ==="
log "\$ $PYTHON_BIN scripts/exchange_smoke_test.py --debug_signing"
if run_and_capture "\"$PYTHON_BIN\" scripts/exchange_smoke_test.py --debug_signing"; then
  SMOKE_LINE="$(grep '^SMOKE_RESULT ' <<<"$LAST_OUTPUT" | tail -n1 || true)"
  if [ -n "$SMOKE_LINE" ]; then
    SMOKE_STATUS="$(parse_smoke_field "$SMOKE_LINE" "status")"
    SMOKE_REASON="$(parse_smoke_field "$SMOKE_LINE" "reason")"
    if [ "$SMOKE_STATUS" = "PASS" ]; then
      append_step "$STEP" "PASS" 0 "${SMOKE_REASON:-ok}"
    elif [ "$SMOKE_STATUS" = "WARN" ]; then
      append_step "$STEP" "WARN" 0 "${SMOKE_REASON:-SMOKE_WARN}"
      update_overall_for_warn
      add_warn_remediation "exchange smoke: python3 scripts/exchange_smoke_test.py --mode TIME --timeout_sec 20 --debug_signing"
    elif [ "$SMOKE_REASON" = "ENV_MISSING_KEYS" ]; then
      append_step "$STEP" "WARN" 1 "ENV_MISSING_KEYS"
      update_overall_for_warn
      add_warn_remediation "exchange smoke env: export BINANCE_API_KEY=... && export BINANCE_API_SECRET=..."
      add_warn_remediation "exchange smoke template: cp .env.example .env && export \$(grep -v '^#' .env | xargs)"
    else
      append_step "$STEP" "FAIL" 1 "${SMOKE_REASON:-SMOKE_FAIL}"
      mark_fail 1 "exchange smoke test failed"
    fi
  else
    append_step "$STEP" "PASS" 0 "ok"
  fi
else
  STEP_CMD_RC=$?
  SMOKE_LINE="$(grep '^SMOKE_RESULT ' <<<"$LAST_OUTPUT" | tail -n1 || true)"
  if [ -n "$SMOKE_LINE" ]; then
    SMOKE_STATUS="$(parse_smoke_field "$SMOKE_LINE" "status")"
    SMOKE_REASON="$(parse_smoke_field "$SMOKE_LINE" "reason")"
    if [ "$SMOKE_STATUS" = "WARN" ]; then
      append_step "$STEP" "WARN" "$STEP_CMD_RC" "${SMOKE_REASON:-SMOKE_WARN}"
      update_overall_for_warn
      EXTERNAL_EVENTS+=("${STEP} (rc=${STEP_CMD_RC})")
      add_warn_remediation "exchange smoke: python3 scripts/exchange_smoke_test.py --mode TIME --timeout_sec 20 --debug_signing"
    elif [ "$SMOKE_REASON" = "ENV_MISSING_KEYS" ]; then
      append_step "$STEP" "WARN" "$STEP_CMD_RC" "ENV_MISSING_KEYS"
      update_overall_for_warn
      add_warn_remediation "exchange smoke env: export BINANCE_API_KEY=... && export BINANCE_API_SECRET=..."
      add_warn_remediation "exchange smoke template: cp .env.example .env && export \$(grep -v '^#' .env | xargs)"
    elif [ "$SMOKE_STATUS" = "FAIL" ]; then
      append_step "$STEP" "FAIL" "$STEP_CMD_RC" "${SMOKE_REASON:-SMOKE_FAIL}"
      mark_fail "$STEP_CMD_RC" "exchange smoke test failed"
    else
      append_step "$STEP" "FAIL" "$STEP_CMD_RC" "exchange smoke test failed"
      mark_fail "$STEP_CMD_RC" "exchange smoke test failed"
    fi
  elif is_external_failure "$LAST_OUTPUT"; then
    append_step "$STEP" "WARN" "$STEP_CMD_RC" "NETWORK_ERROR"
    EXTERNAL_EVENTS+=("${STEP} (rc=${STEP_CMD_RC})")
    update_overall_for_warn
    add_warn_remediation "exchange smoke: python3 scripts/exchange_smoke_test.py --mode TIME --timeout_sec 20 --debug_signing"
  else
    append_step "$STEP" "FAIL" "$STEP_CMD_RC" "exchange smoke test failed"
    mark_fail "$STEP_CMD_RC" "exchange smoke test failed"
  fi
fi
stop_if_failed

# Step 10: execute paper
STEP="python3 scripts/execute_paper.py --debug_signing"
log ""
log "=== ${STEP} ==="
log "\$ $PYTHON_BIN scripts/execute_paper.py --debug_signing"
if run_and_capture "\"$PYTHON_BIN\" scripts/execute_paper.py --debug_signing"; then
  append_step "$STEP" "PASS" 0 "ok"
else
  STEP_CMD_RC=$?
  if is_external_failure "$LAST_OUTPUT"; then
    append_step "$STEP" "WARN" "$STEP_CMD_RC" "external/network degradation"
    EXTERNAL_EVENTS+=("${STEP} (rc=${STEP_CMD_RC})")
    update_overall_for_warn
  else
    append_step "$STEP" "FAIL" "$STEP_CMD_RC" "execute_paper failed"
    mark_fail "$STEP_CMD_RC" "execute_paper failed"
  fi
fi
stop_if_failed

# Step 11: reconcile
STEP="python3 scripts/order_reconcile.py"
log ""
log "=== ${STEP} ==="
log "\$ $PYTHON_BIN scripts/order_reconcile.py"
if run_and_capture "\"$PYTHON_BIN\" scripts/order_reconcile.py"; then
  append_step "$STEP" "PASS" 0 "ok"
  write_reconcile_json "DONE" "order reconcile completed"
else
  STEP_CMD_RC=$?
  if is_external_failure "$LAST_OUTPUT"; then
    append_step "$STEP" "WARN" "$STEP_CMD_RC" "external/network degradation"
    EXTERNAL_EVENTS+=("${STEP} (rc=${STEP_CMD_RC})")
    update_overall_for_warn
    write_reconcile_json "WARN" "order reconcile degraded due to external/network issue"
  else
    append_step "$STEP" "FAIL" "$STEP_CMD_RC" "order reconcile failed"
    write_reconcile_json "FAILED" "order reconcile command failed"
    mark_fail "$STEP_CMD_RC" "order_reconcile failed"
  fi
fi
stop_if_failed

# Step 12: secret leak scan
STEP="secret leak scan"
log ""
log "=== ${STEP} ==="
if scan_secret_leaks; then
  append_step "$STEP" "FAIL" 1 "leak detected"
  mark_fail 1 "secret leak detected in gate outputs"
  write_report
  log "Secret leak detected in gate outputs."
  exit "$EXIT_CODE"
fi
append_step "$STEP" "PASS" 0 "ok"

if [ "$STRICT" = "1" ] && [ "$OVERALL_STATUS" = "WARN" ]; then
  OVERALL_STATUS="FAIL"
  EXIT_CODE=1
  STOP_REASON="strict mode treats warnings as failures"
fi

write_report
log "gate_all completed with ${OVERALL_STATUS}. Report: ${REPORT_PATH}"
exit "$EXIT_CODE"
