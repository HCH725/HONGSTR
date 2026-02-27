#!/usr/bin/env bash
# HONGSTR worker: continuous backtest sweep runner (report_only)
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[worker_backtests] macOS only. Detected: $(uname -s)" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f ".env.worker" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.worker
  set +a
fi

RUN_MINUTES="${HONGSTR_WORKER_RUN_MINUTES:-40}"
SLEEP_MINUTES="${HONGSTR_WORKER_SLEEP_MINUTES:-10}"
BETWEEN_RUNS_SECONDS="${HONGSTR_WORKER_BETWEEN_RUNS_SECONDS:-5}"
STATE_DIR="${HONGSTR_WORKER_STATE_DIR:-_local/worker_state}"
TARGET_BRANCH="${HONGSTR_WORKER_MAIN_BRANCH:-main}"
ONCE_MODE="${HONGSTR_WORKER_ONCE:-0}"
MAX_CYCLES="${HONGSTR_WORKER_MAX_CYCLES:-0}"
SYMBOLS="${HONGSTR_WORKER_BACKTEST_SYMBOLS:-BTCUSDT ETHUSDT BNBUSDT}"
TIMEFRAMES="${HONGSTR_WORKER_BACKTEST_TIMEFRAMES:-1h,4h}"
START_DATE="${HONGSTR_WORKER_BACKTEST_START:-2020-01-01}"
END_DATE="${HONGSTR_WORKER_BACKTEST_END:-now}"

mkdir -p "$STATE_DIR"
HEARTBEAT_PATH="$STATE_DIR/worker_heartbeat.json"
LAST_RUN_PATH="$STATE_DIR/last_run_backtests.json"
LOG_PATH="$STATE_DIR/backtests_worker.log"

if [[ ! -x "./.venv/bin/python" ]]; then
  echo "[worker_backtests] missing .venv; run bootstrap first" >&2
  exit 1
fi

write_heartbeat() {
  local phase="$1"
  local status="$2"
  local message="$3"
  ./.venv/bin/python - "$HEARTBEAT_PATH" "$phase" "$status" "$message" "$RUN_MINUTES" "$SLEEP_MINUTES" <<'PY'
import datetime as dt
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
phase = sys.argv[2]
status = sys.argv[3]
message = sys.argv[4]
run_minutes = int(sys.argv[5])
sleep_minutes = int(sys.argv[6])
now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
payload = {
    "ts_utc": now,
    "job": "backtests",
    "phase": phase,
    "status": status,
    "message": message,
    "schedule": {
        "run_minutes": run_minutes,
        "sleep_minutes": sleep_minutes,
    },
}
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
}

write_last_run() {
  local start_utc="$1"
  local end_utc="$2"
  local exit_code="$3"
  local status="$4"
  local reason="$5"
  local git_sha="$6"
  local branch="$7"
  local out_dir="$8"
  local symbols_val="$9"
  local timeframes_val="${10}"
  local start_val="${11}"
  local end_val="${12}"
  ./.venv/bin/python - "$LAST_RUN_PATH" "$start_utc" "$end_utc" "$exit_code" "$status" "$reason" "$git_sha" "$branch" "$out_dir" "$symbols_val" "$timeframes_val" "$start_val" "$end_val" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "job": "backtests",
    "started_utc": sys.argv[2],
    "ended_utc": sys.argv[3],
    "exit_code": int(sys.argv[4]),
    "status": sys.argv[5],
    "reason": sys.argv[6],
    "git_sha": sys.argv[7],
    "branch": sys.argv[8],
    "report_only": True,
    "backtest_out_dir": sys.argv[9],
    "params": {
        "symbols": sys.argv[10],
        "timeframes": sys.argv[11],
        "start": sys.argv[12],
        "end": sys.argv[13],
    },
}
path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
}

sync_main_branch() {
  if git fetch origin "$TARGET_BRANCH" >>"$LOG_PATH" 2>&1 && git checkout "$TARGET_BRANCH" >>"$LOG_PATH" 2>&1; then
    git pull --ff-only origin "$TARGET_BRANCH" >>"$LOG_PATH" 2>&1 || true
  fi
}

extract_out_dir() {
  local log_file="$1"
  awk -F': ' '/^OUT_DIR:/{print $2}' "$log_file" | tail -n 1
}

run_once() {
  local start_utc
  local end_utc
  local start_epoch
  local end_epoch
  local git_sha
  local branch
  local rc=0
  local run_log
  local out_dir=""

  start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  start_epoch="$(date -u +%s)"
  run_log="$STATE_DIR/backtests_run_$(date -u +%Y%m%d_%H%M%S).log"

  write_heartbeat "running" "RUN" "backtest sweep started"

  sync_main_branch
  git_sha="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
  branch="$(git branch --show-current 2>/dev/null || echo unknown)"

  {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] run: bash scripts/run_and_verify.sh --mode foreground --no_fail_on_gate --symbols \"${SYMBOLS}\" --timeframes \"${TIMEFRAMES}\" --start \"${START_DATE}\" --end \"${END_DATE}\""
    bash scripts/run_and_verify.sh \
      --mode foreground \
      --no_fail_on_gate \
      --symbols "$SYMBOLS" \
      --timeframes "$TIMEFRAMES" \
      --start "$START_DATE" \
      --end "$END_DATE"
  } >>"$run_log" 2>&1 || rc=$?

  {
    echo "--- $(date -u +%Y-%m-%dT%H:%M:%SZ) completed with rc=${rc} ---"
    cat "$run_log"
  } >>"$LOG_PATH"

  out_dir="$(extract_out_dir "$run_log")"
  end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  end_epoch="$(date -u +%s)"

  local status="PASS"
  local reason="completed"
  if [[ "$rc" -ne 0 ]]; then
    status="WARN"
    reason="backtest sweep returned non-zero"
  fi

  write_last_run "$start_utc" "$end_utc" "$rc" "$status" "$reason" "$git_sha" "$branch" "$out_dir" "$SYMBOLS" "$TIMEFRAMES" "$START_DATE" "$END_DATE"
  write_heartbeat "running" "$status" "backtests run finished in $((end_epoch - start_epoch))s"
  echo "[worker_backtests] run status=$status rc=$rc duration=$((end_epoch - start_epoch))s out_dir=$out_dir"
}

run_seconds=$((RUN_MINUTES * 60))
sleep_seconds=$((SLEEP_MINUTES * 60))
cycle=0

while true; do
  cycle=$((cycle + 1))
  window_start="$(date -u +%s)"
  window_end=$((window_start + run_seconds))

  write_heartbeat "run_window" "RUN" "cycle=${cycle} run_window_started"

  while [[ "$(date -u +%s)" -lt "$window_end" ]]; do
    run_once

    if [[ "$ONCE_MODE" == "1" ]]; then
      write_heartbeat "done" "PASS" "once mode complete"
      exit 0
    fi

    if [[ "$MAX_CYCLES" -gt 0 && "$cycle" -ge "$MAX_CYCLES" ]]; then
      write_heartbeat "done" "PASS" "max cycles reached"
      exit 0
    fi

    if [[ "$(date -u +%s)" -lt "$window_end" ]]; then
      sleep "$BETWEEN_RUNS_SECONDS"
    fi
  done

  write_heartbeat "sleep" "IDLE" "cooldown ${SLEEP_MINUTES}m"
  sleep "$sleep_seconds"
done
