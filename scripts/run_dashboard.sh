#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST_127="127.0.0.1"
PORT="${PORT:-8501}"
OPEN_SAFARI=0
LOG_FILE="${LOG_FILE:-}"

usage() {
  cat <<'EOF'
Usage: bash scripts/run_dashboard.sh [options]

Options:
  --port PORT            Default: 8501
  --log-file PATH        Default: /tmp/hongstr_streamlit_<PORT>.log
  --open-safari          Open Safari after startup
  -h, --help             Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --log-file) LOG_FILE="$2"; shift 2 ;;
    --open-safari) OPEN_SAFARI=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$LOG_FILE" ]]; then
  LOG_FILE="/tmp/hongstr_streamlit_${PORT}.log"
fi
PID_FILE="/tmp/hongstr_streamlit_${PORT}.pid"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
else
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 -m pip -q show streamlit >/dev/null || python3 -m pip -q install streamlit >/dev/null
python3 -m pip -q show pandas >/dev/null || python3 -m pip -q install pandas >/dev/null

if command -v lsof >/dev/null 2>&1; then
  old_pids="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$old_pids" ]]; then
    kill $old_pids 2>/dev/null || true
    sleep 0.3
  fi
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(tr -d '[:space:]' < "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" 2>/dev/null || true
    sleep 0.3
  fi
  rm -f "$PID_FILE" || true
fi

rm -f "$LOG_FILE" || true
nohup streamlit run scripts/dashboard.py \
  --server.address "$HOST_127" \
  --server.port "$PORT" \
  --server.headless true \
  < /dev/null >"$LOG_FILE" 2>&1 &
spid=$!
echo "$spid" > "$PID_FILE"

for _ in $(seq 1 40); do
  if ! kill -0 "$spid" 2>/dev/null; then
    echo "ERROR: streamlit exited unexpectedly"
    tail -n 120 "$LOG_FILE" || true
    exit 3
  fi
  if ! lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    sleep 0.25
    continue
  fi
  if curl -fsS "http://$HOST_127:$PORT/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

if ! kill -0 "$spid" 2>/dev/null; then
  echo "ERROR: streamlit is not running (pid=$spid)"
  tail -n 120 "$LOG_FILE" || true
  exit 4
fi
if ! lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: streamlit did not bind port $PORT"
  tail -n 120 "$LOG_FILE" || true
  exit 5
fi
if ! curl -fsS "http://$HOST_127:$PORT/" >/dev/null 2>&1; then
  echo "ERROR: HTTP probe failed for http://$HOST_127:$PORT/"
  tail -n 120 "$LOG_FILE" || true
  exit 6
fi

if [[ -f scripts/healthcheck_dashboard.sh ]]; then
  PORT="$PORT" PID_FILE="$PID_FILE" LOG_FILE="$LOG_FILE" bash scripts/healthcheck_dashboard.sh
fi

echo "URL_127=http://$HOST_127:$PORT/"
echo "URL_LOCALHOST=http://localhost:$PORT/"
if ! curl -fsS "http://localhost:$PORT/" >/dev/null 2>&1; then
  echo "WARN: localhost probe failed (possible IPv6 ::1 issue). Use URL_127."
fi
echo "PIDFILE=$PID_FILE"
echo "STREAMLIT_LOG=$LOG_FILE"

if [[ "$OPEN_SAFARI" -eq 1 ]] && command -v open >/dev/null 2>&1; then
  open -a "Safari" "http://$HOST_127:$PORT/?ts=$(date +%s)" || true
fi
