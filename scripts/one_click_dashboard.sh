#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"
START_DATE="2024-01-01"
END_DATE="now"
HOST="127.0.0.1"
HOST_127="127.0.0.1"
PORT="8501"
SYNC_MAIN=0
SKIP_BENCHMARK=0
SKIP_WALKFORWARD=0
OPEN_SAFARI=0
LOG_PIPE="/tmp/hongstr_dashboard_pipeline.log"
LOG_ST="/tmp/hongstr_streamlit_8501.log"

usage() {
  cat <<'EOF'
Usage: bash scripts/one_click_dashboard.sh [options]

Options:
  --symbols CSV             Default: BTCUSDT,ETHUSDT,BNBUSDT
  --start YYYY-MM-DD        Default: 2024-01-01
  --end DATE|now            Default: now
  --host HOST               Default: 127.0.0.1
  --port PORT               Default: 8501
  --sync-main               git checkout main && git pull --ff-only
  --skip-benchmark          Skip scripts/benchmark_suite.sh
  --skip-walkforward        Skip scripts/walkforward_suite.sh --quick
  --open-safari             Open Safari with cache-busting URL at the end
  --log-pipe PATH           Default: /tmp/hongstr_dashboard_pipeline.log
  --log-streamlit PATH      Default: /tmp/hongstr_streamlit_8501.log
  -h, --help                Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --start) START_DATE="$2"; shift 2 ;;
    --end) END_DATE="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --sync-main) SYNC_MAIN=1; shift ;;
    --skip-benchmark) SKIP_BENCHMARK=1; shift ;;
    --skip-walkforward) SKIP_WALKFORWARD=1; shift ;;
    --open-safari) OPEN_SAFARI=1; shift ;;
    --log-pipe) LOG_PIPE="$2"; shift 2 ;;
    --log-streamlit) LOG_ST="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

normalize_csv_symbols() {
  local raw="${1:-}"
  if [[ -z "$raw" ]]; then
    echo ""
    return
  fi
  local squashed
  squashed="$(echo "$raw" | tr ',\t\r\n' '    ' | xargs 2>/dev/null || true)"
  if [[ -z "$squashed" ]]; then
    echo ""
    return
  fi
  echo "$squashed" | tr ' ' ','
}

SYMBOLS="$(normalize_csv_symbols "$SYMBOLS")"
if [[ -z "$SYMBOLS" ]]; then
  SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"
fi

echo "=== [0] SNAPSHOT ==="
pwd
git rev-parse --abbrev-ref HEAD
git log -1 --oneline
git status -sb

if [[ "$SYNC_MAIN" -eq 1 ]]; then
  echo "=== [0.1] SYNC MAIN ==="
  git fetch origin --prune
  git checkout main
  git pull --ff-only
fi

echo "=== [1] VENV + DEPS ==="
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
else
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi
python3 -V
python3 -m pip -q install -U pip >/dev/null || echo "WARN: pip upgrade skipped (offline/blocked)"
if [[ -f requirements.txt ]]; then
  python3 -m pip -q install -r requirements.txt >/dev/null || echo "WARN: requirements install skipped (offline/blocked)"
fi
if ! python3 -m pip -q show streamlit >/dev/null; then
  python3 -m pip -q install streamlit >/dev/null
fi

echo "=== [2] PREP DATA (prefer local parquet -> derived) ==="
set +e
python3 scripts/sync_derived_from_parquet.py \
  --symbols "$SYMBOLS" \
  --start "$START_DATE" \
  --end "$END_DATE" \
  --tfs "1h,4h"
SYNC_RC=$?
set -e
if [[ "$SYNC_RC" -ne 0 ]]; then
  echo "WARN: sync_derived_from_parquet failed rc=$SYNC_RC, fallback to ingest+aggregate"
  IFS=',' read -r -a SYM_ARR <<< "$SYMBOLS"
  for sym in "${SYM_ARR[@]}"; do
    sym="$(echo "$sym" | xargs)"
    [[ -z "$sym" ]] && continue
    python3 scripts/ingest_historical.py --symbol "$sym" --start "$START_DATE" --end "$END_DATE"
    python3 scripts/aggregate_data.py --symbol "$sym" --tfs "1h,4h"
  done
fi

echo "=== [2.1] BAR COUNTS ==="
python3 - "$SYMBOLS" <<'PY'
import json
import sys
from pathlib import Path

symbols = [s.strip() for s in sys.argv[1].split(",") if s.strip()]
for sym in symbols:
    for tf in ["1m", "1h", "4h"]:
        p = Path("data/derived") / sym / tf / "klines.jsonl"
        n = 0
        first = None
        last = None
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    n += 1
                    try:
                        ts = json.loads(line).get("ts")
                    except Exception:
                        ts = None
                    if isinstance(ts, int):
                        if first is None:
                            first = ts
                        last = ts
        print(f"{sym} {tf} rows={n} first_ts={first} last_ts={last}")
PY

echo "=== [3] RUN BACKTEST PIPELINE ==="
: > "$LOG_PIPE"
set +e
bash scripts/run_and_verify.sh \
  --no_fail_on_gate \
  --mode foreground \
  --symbols "$SYMBOLS" \
  --timeframes "1h,4h" \
  --start "$START_DATE" \
  --end "$END_DATE" 2>&1 | tee "$LOG_PIPE"
PIPE_RC=${PIPESTATUS[0]}
set -e
echo "run_and_verify rc=$PIPE_RC"

LATEST_RUN_DIR="$(grep -E 'OUT_DIR:' "$LOG_PIPE" | tail -n 1 | awk '{print $2}')"
if [[ -z "$LATEST_RUN_DIR" || ! -d "$LATEST_RUN_DIR" ]]; then
  LATEST_RUN_DIR="$(ls -1dt data/backtests/*/* 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$LATEST_RUN_DIR" || ! -d "$LATEST_RUN_DIR" ]]; then
  echo "ERROR: cannot resolve latest run dir" >&2
  exit 3
fi
echo "LATEST_RUN_DIR=$LATEST_RUN_DIR"
MAIN_RUN_DIR="$LATEST_RUN_DIR"

echo "=== [3.1] ENSURE RUN ARTIFACTS ==="
python3 scripts/generate_selection_artifact.py --run_dir "$LATEST_RUN_DIR" || true
python3 scripts/generate_action_items.py --data_dir data || true

if [[ "$SKIP_BENCHMARK" -eq 0 ]]; then
  echo "=== [3.2] BENCHMARK SUITE ==="
  set +e
  bash scripts/benchmark_suite.sh --symbols "$SYMBOLS" --start_full "$START_DATE" 2>&1 | tee -a "$LOG_PIPE"
  BENCH_RC=${PIPESTATUS[0]}
  set -e
  echo "benchmark_suite rc=$BENCH_RC"
else
  BENCH_RC=0
fi

if [[ "$SKIP_WALKFORWARD" -eq 0 ]]; then
  echo "=== [3.3] WALKFORWARD QUICK ==="
  set +e
  bash scripts/walkforward_suite.sh --quick --symbols "$SYMBOLS" 2>&1 | tee -a "$LOG_PIPE"
  WF_RC=${PIPESTATUS[0]}
  set -e
  echo "walkforward_suite rc=$WF_RC"
  set +e
  python3 scripts/report_walkforward.py --suite_mode QUICK 2>&1 | tee -a "$LOG_PIPE"
  WFR_RC=${PIPESTATUS[0]}
  set -e
  echo "report_walkforward rc=$WFR_RC"
else
  WF_RC=0
  WFR_RC=0
fi

echo "=== [3.4] FALLBACK LATEST ARTIFACTS ==="
python3 - "$LATEST_RUN_DIR" <<'PY'
import json
from datetime import datetime
from pathlib import Path
import tempfile

run_dir = Path(__import__("sys").argv[1]).resolve()
reports = Path("reports")
reports.mkdir(parents=True, exist_ok=True)

def load(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(payload, tmp, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)

summary = load(run_dir / "summary.json") or {}
gate = load(run_dir / "gate.json") or {}

bench_path = reports / "benchmark_latest.json"
bench = load(bench_path)
if not bench:
    payload = {
        "schema_version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "paths": {
            "FULL": str(run_dir / "summary.json"),
            "SHORT": str(run_dir / "summary.json"),
        },
        "FULL": {
            "run_dir": str(run_dir),
            "top": summary,
            "per_symbol_4h": summary.get("per_symbol", {}),
            "gate_overall": gate.get("results", {}).get("overall", {"pass": False, "reasons": ["gate.json missing"]}),
        },
        "SHORT": {
            "run_dir": str(run_dir),
            "top": summary,
            "per_symbol_4h": summary.get("per_symbol", {}),
            "gate_overall": gate.get("results", {}).get("overall", {"pass": False, "reasons": ["gate.json missing"]}),
        },
    }
    atomic_json(bench_path, payload)

wf_latest = reports / "walkforward_latest.json"
wf = load(wf_latest)
if not wf:
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "run_id": run_dir.name,
        "suite_mode": "FALLBACK_SINGLE_RUN",
        "status": "PARTIAL",
        "windows_total": 1,
        "windows_completed": 1,
        "windows_failed": 0,
        "windows": [
            {
                "name": "LATEST_SINGLE_RUN",
                "start": summary.get("start_ts"),
                "end": summary.get("end_ts"),
                "status": "COMPLETED",
                "run_dir": str(run_dir),
                "gate_overall": "PASS" if gate.get("results", {}).get("overall", {}).get("pass") else "FAIL",
                "selection_decision": "UNKNOWN",
                "sharpe": summary.get("sharpe"),
                "mdd": summary.get("max_drawdown"),
                "total_return": summary.get("total_return"),
                "trades": summary.get("trades_count"),
                "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
                "failure_reason": "",
            }
        ],
        "stability": {},
        "latest_updated": True,
        "latest_warning_reason": "LATEST_UPDATED_FALLBACK_SINGLE_RUN",
        "latest_update_reason": "generated by one_click_dashboard fallback",
        "latest_update_path": str(wf_latest),
        "latest_pointer_policy": "allow_update_fallback_single_run",
    }
    atomic_json(wf_latest, payload)

orders_path = reports / "orders_latest.json"
existing_orders = load(orders_path)
if isinstance(existing_orders, dict):
    existing_orders["last_backtest_synced_at"] = datetime.utcnow().isoformat() + "Z"
    existing_orders["last_backtest_run_dir"] = str(run_dir)
    if not isinstance(existing_orders.get("orders"), list):
        existing_orders["orders"] = []
    atomic_json(orders_path, existing_orders)
else:
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "BACKTEST_FALLBACK",
        "run_dir": str(run_dir),
        "orders": [],
        "note": "No paper/live execution orders for backtest run.",
    }
    atomic_json(orders_path, payload)
PY

echo "=== [3.5] PROMOTE MAIN RUN FOR DASHBOARD DEFAULT ==="
if [[ -n "${MAIN_RUN_DIR:-}" && -f "$MAIN_RUN_DIR/summary.json" ]]; then
  touch "$MAIN_RUN_DIR/summary.json" || true
  echo "PROMOTED_RUN=$MAIN_RUN_DIR"
fi

echo "=== [3.6] RESYNC ACTION ITEMS TO PROMOTED RUN ==="
python3 scripts/generate_action_items.py --data_dir data || true

echo "=== [4] RESTART STREAMLIT ==="
if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -ti tcp:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$PIDS" ]]; then
    kill $PIDS 2>/dev/null || true
  fi
fi
for pidfile in "/tmp/hongstr_streamlit_${PORT}.pid" "/tmp/hongstr_streamlit_$((PORT + 1)).pid"; do
  if [[ -f "$pidfile" ]]; then
    old_pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
      kill "$old_pid" 2>/dev/null || true
    fi
    rm -f "$pidfile" || true
  fi
done
sleep 0.5

ACTIVE_PORT="$PORT"
start_streamlit() {
  local p="$1"
  local pidfile="/tmp/hongstr_streamlit_${p}.pid"
  rm -f "$LOG_ST" "$pidfile" || true
  nohup streamlit run scripts/dashboard.py \
    --server.address "$HOST_127" \
    --server.port "$p" \
    --server.headless true \
    < /dev/null >"$LOG_ST" 2>&1 &
  local spid=$!
  disown "$spid" 2>/dev/null || true
  echo "$spid" > "$pidfile"
  sleep 1
  if ! kill -0 "$spid" 2>/dev/null; then
    return 1
  fi
  for _ in $(seq 1 40); do
    if ! kill -0 "$spid" 2>/dev/null; then
      return 1
    fi
    if ! lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
      sleep 0.25
      continue
    fi
    if curl -fsS "http://$HOST_127:$p/" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

if ! start_streamlit "$ACTIVE_PORT"; then
  echo "WARN: streamlit failed on :$ACTIVE_PORT, trying :$((ACTIVE_PORT + 1))"
  ACTIVE_PORT="$((ACTIVE_PORT + 1))"
  if ! start_streamlit "$ACTIVE_PORT"; then
    echo "ERROR: streamlit failed to start on both ports"
    tail -n 120 "$LOG_ST" || true
    exit 4
  fi
fi

echo "=== [5] SMOKE ==="
if ! lsof -nP -iTCP:"$ACTIVE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: port $ACTIVE_PORT is not listening after startup"
  tail -n 120 "$LOG_ST" || true
  exit 5
fi
if ! curl -fsS "http://$HOST_127:$ACTIVE_PORT/" >/dev/null; then
  echo "ERROR: HTTP check failed on http://$HOST_127:$ACTIVE_PORT/"
  tail -n 120 "$LOG_ST" || true
  exit 6
fi
echo "HTTP_OK http://$HOST_127:$ACTIVE_PORT/"

echo "=== [5.1] STREAMLIT ERROR SCAN ==="
if egrep -n "Traceback|Exception|NoneType.__format__|unsupported format string passed to NoneType" "$LOG_ST"; then
  echo "WARN: fatal patterns detected in streamlit log"
else
  echo "OK: no fatal patterns in streamlit log"
fi

echo "=== [6] ARTIFACT SNAPSHOT ==="
for p in \
  "reports/benchmark_latest.json" \
  "reports/walkforward_latest.json" \
  "reports/action_items_latest.json" \
  "reports/orders_latest.json" \
  "$LATEST_RUN_DIR/summary.json" \
  "$LATEST_RUN_DIR/gate.json" \
  "$LATEST_RUN_DIR/regime_report.json" \
  "$LATEST_RUN_DIR/optimizer.json" \
  "$LATEST_RUN_DIR/optimizer_regime.json" \
  "$LATEST_RUN_DIR/selection.json"
do
  if [[ -f "$p" ]]; then
    ls -lhT "$p"
  else
    echo "MISSING $p"
  fi
done

echo "=== DONE ==="
echo "URL_127=http://$HOST_127:$ACTIVE_PORT/"
echo "URL_LOCALHOST=http://localhost:$ACTIVE_PORT/"
if ! curl -fsS "http://localhost:$ACTIVE_PORT/" >/dev/null 2>&1; then
  echo "WARN: localhost may resolve to IPv6 (::1) on some Macs. Prefer URL_127=http://$HOST_127:$ACTIVE_PORT/"
fi
echo "PIDFILE=/tmp/hongstr_streamlit_${ACTIVE_PORT}.pid"
echo "LATEST_RUN_DIR=$LATEST_RUN_DIR"
echo "PIPELINE_LOG=$LOG_PIPE"
echo "STREAMLIT_LOG=$LOG_ST"

if [[ "$OPEN_SAFARI" -eq 1 ]]; then
  if command -v open >/dev/null 2>&1; then
    open -a "Safari" "http://$HOST_127:$ACTIVE_PORT/?ts=$(date +%s)" || true
  fi
fi
