#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-8501}"
HOST_127="127.0.0.1"
LOG_FILE="${LOG_FILE:-/tmp/hongstr_streamlit_${PORT}.log}"
PID_FILE="${PID_FILE:-/tmp/hongstr_streamlit_${PORT}.pid}"

echo "=== dashboard healthcheck ==="
echo "ROOT=$ROOT_DIR"
echo "PORT=$PORT"
echo "PID_FILE=$PID_FILE"
echo "LOG_FILE=$LOG_FILE"

PID=""
if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
fi

if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
  echo "PID_ALIVE=$PID"
else
  echo "PID_ALIVE=NO"
fi

echo "== lsof =="
if ! lsof -nP -iTCP:"$PORT" -sTCP:LISTEN; then
  echo "FAIL: no LISTEN on $HOST_127:$PORT"
  [[ -f "$LOG_FILE" ]] && tail -n 80 "$LOG_FILE" || true
  exit 1
fi

echo "== curl 127 =="
if ! curl -fsS -D - "http://$HOST_127:$PORT/" -o /dev/null | head -n 5; then
  echo "FAIL: HTTP check failed for http://$HOST_127:$PORT/"
  [[ -f "$LOG_FILE" ]] && tail -n 80 "$LOG_FILE" || true
  exit 1
fi

echo "== curl localhost =="
if ! curl -fsS -D - "http://localhost:$PORT/" -o /dev/null | head -n 5; then
  echo "WARN: localhost failed; use http://$HOST_127:$PORT/"
fi

echo "PASS: dashboard healthy on http://$HOST_127:$PORT/"
