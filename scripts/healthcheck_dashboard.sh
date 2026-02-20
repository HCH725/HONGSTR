#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST_127="${HOST_127:-127.0.0.1}"
PORT="${PORT:-}"
PID_FILE="${PID_FILE:-}"
LOG_FILE="${LOG_FILE:-}"
PID=""

print_logs() {
  local log_candidate=""
  if [[ -n "${LOG_FILE:-}" && -f "$LOG_FILE" ]]; then
    log_candidate="$LOG_FILE"
  elif [[ -n "${PORT:-}" && -f "/tmp/hongstr_streamlit_${PORT}.log" ]]; then
    log_candidate="/tmp/hongstr_streamlit_${PORT}.log"
  elif [[ -f "/tmp/hongstr_streamlit_8501.log" ]]; then
    log_candidate="/tmp/hongstr_streamlit_8501.log"
  elif [[ -f "/tmp/hongstr_streamlit_8502.log" ]]; then
    log_candidate="/tmp/hongstr_streamlit_8502.log"
  fi

  if [[ -n "$log_candidate" ]]; then
    echo "LOG_FILE=$log_candidate"
    tail -n 120 "$log_candidate" || true
  else
    echo "LOG_FILE=NOT_FOUND"
  fi
}

fail() {
  echo "FAIL: $1"
  print_logs
  exit 1
}

probe_pidfile_port() {
  local p="$1"
  local pidfile="/tmp/hongstr_streamlit_${p}.pid"
  [[ -f "$pidfile" ]] || return 1

  local pid
  pid="$(tr -d '[:space:]' < "$pidfile" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    echo "WARN: empty pidfile removed: $pidfile"
    rm -f "$pidfile" || true
    return 1
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "WARN: stale pidfile removed: $pidfile (pid=$pid)"
    rm -f "$pidfile" || true
    return 1
  fi

  PORT="$p"
  PID="$pid"
  PID_FILE="$pidfile"
  return 0
}

auto_detect_port() {
  local p
  for p in 8501 8502; do
    if probe_pidfile_port "$p"; then
      return 0
    fi
  done

  for p in $(seq 8501 8510); do
    if lsof -nP -iTCP:"$p" -sTCP:LISTEN 2>/dev/null | awk 'NR>1 && ($1 ~ /python|streamlit/) {found=1} END{exit !found}'; then
      PORT="$p"
      PID="$(lsof -nP -iTCP:"$p" -sTCP:LISTEN 2>/dev/null | awk 'NR>1 && ($1 ~ /python|streamlit/) {print $2; exit}')"
      return 0
    fi
  done

  return 1
}

if [[ -z "$PORT" ]]; then
  auto_detect_port || fail "cannot detect dashboard port (8501-8510)"
fi

if [[ -z "$PID_FILE" ]]; then
  if [[ -f "/tmp/hongstr_streamlit_${PORT}.pid" ]]; then
    PID_FILE="/tmp/hongstr_streamlit_${PORT}.pid"
  fi
fi
if [[ -z "$LOG_FILE" ]]; then
  LOG_FILE="/tmp/hongstr_streamlit_${PORT}.log"
fi

echo "=== dashboard healthcheck ==="
echo "ROOT=$ROOT_DIR"
echo "PORT=$PORT"
echo "PID_FILE=${PID_FILE:-N/A}"
echo "LOG_FILE=$LOG_FILE"

if [[ -n "${PID_FILE:-}" && -f "$PID_FILE" ]]; then
  PID="$(tr -d '[:space:]' < "$PID_FILE" 2>/dev/null || true)"
  [[ -n "$PID" ]] || fail "pidfile exists but empty: $PID_FILE"
  kill -0 "$PID" 2>/dev/null || fail "pidfile points to dead process: pid=$PID ($PID_FILE)"
  echo "PID_ALIVE=$PID"
else
  echo "PID_ALIVE=UNKNOWN (no pidfile)"
fi

echo "== lsof =="
LSOF_OUT="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
[[ -n "$LSOF_OUT" ]] || fail "no LISTEN on $HOST_127:$PORT"
echo "$LSOF_OUT"

echo "== curl 127 =="
HEADERS_127="$(curl -fsS -D - "http://$HOST_127:$PORT/" -o /dev/null | head -n 5 || true)"
[[ -n "$HEADERS_127" ]] || fail "HTTP probe failed for http://$HOST_127:$PORT/"
echo "$HEADERS_127"
if ! grep -qE '^HTTP/[0-9.]+ 200' <<< "$HEADERS_127"; then
  fail "unexpected HTTP status for http://$HOST_127:$PORT/"
fi

echo "== curl localhost =="
if ! curl -fsS -D - "http://localhost:$PORT/" -o /dev/null | head -n 5; then
  echo "WARN: localhost probe failed (possible IPv6 ::1 resolution issue). Use http://$HOST_127:$PORT/"
fi

echo "PASS: dashboard healthy on http://$HOST_127:$PORT/"
