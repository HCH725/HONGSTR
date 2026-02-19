#!/bin/bash
# scripts/walkforward_suite.sh
# Automate Walk-Forward / Regime Dataset Batch Processing with run-id versioned outputs.

set -u -o pipefail

QUICK_MODE=false
CONFIG_FILE="configs/windows.json"
DATA_ROOT="data"
REPORTS_DIR="reports"
SYMBOLS_OVERRIDE=""
RUNNER_SCRIPT="scripts/run_and_verify.sh"
ENSURE_SCRIPT="scripts/ensure_quick_data.sh"
SKIP_ENSURE_DATA=false

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --quick) QUICK_MODE=true ;;
    --config) CONFIG_FILE="$2"; shift ;;
    --symbols) SYMBOLS_OVERRIDE="$2"; shift ;;
    --runner_script) RUNNER_SCRIPT="$2"; shift ;;
    --ensure_script) ENSURE_SCRIPT="$2"; shift ;;
    --skip_ensure_data) SKIP_ENSURE_DATA=true ;;
    *) echo "Unknown parameter passed: $1"; exit 1 ;;
  esac
  shift
done

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: Config file $CONFIG_FILE not found."
  exit 1
fi

RUN_TS="$(date -u +"%Y%m%d_%H%M%S")"
GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo "nogit")"
RUN_ID="${RUN_TS}_${GIT_SHA}"
WF_ROOT="${REPORTS_DIR}/walkforward"
WF_RUN_DIR="${WF_ROOT}/${RUN_ID}"
RESULTS_TSV="${WF_RUN_DIR}/suite_results.tsv"

mkdir -p "$WF_RUN_DIR"
: > "$RESULTS_TSV"
DIAG_TSV="${WF_RUN_DIR}/failure_diagnostics.tsv"
: > "$DIAG_TSV"

sanitize_field() {
  local raw="${1:-}"
  raw="${raw//$'\t'/ }"
  raw="${raw//$'\n'/ }"
  echo "$raw"
}

classify_failure_reason() {
  local output="${1:-}"
  local exit_code="${2:-1}"
  if grep -q "Insufficient data for resampling" <<<"$output"; then
    echo "INSUFFICIENT_DATA_RESAMPLE"
    return
  fi
  if grep -q "No data for" <<<"$output"; then
    echo "NO_DATA_IN_RANGE"
    return
  fi
  if grep -q "No backtest results produced." <<<"$output"; then
    echo "NO_BACKTEST_RESULTS"
    return
  fi
  if grep -q "unsupported format string passed to NoneType.__format__" <<<"$output"; then
    echo "GATE_SUMMARY_FORMAT_ERROR"
    return
  fi
  echo "pipeline_exit_${exit_code}"
}

echo "=== Walk-Forward Suite ==="
echo "Config: $CONFIG_FILE"
echo "Quick Mode: $QUICK_MODE"
echo "Run ID: $RUN_ID"
echo "Run Dir: $WF_RUN_DIR"

WINDOWS_JSON="$(cat "$CONFIG_FILE")"
if [ "$QUICK_MODE" = true ]; then
  WINDOWS_JSON="$(echo "$WINDOWS_JSON" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)[:2]))")"
  SYMBOLS="${SYMBOLS_OVERRIDE:-BTCUSDT}"
  echo "Quick Mode: Running first 2 windows, Symbols: $SYMBOLS"
  if [ "$SKIP_ENSURE_DATA" = false ]; then
    echo "=== Ensuring quick local data ==="
    if [ -x "$ENSURE_SCRIPT" ] || [ -f "$ENSURE_SCRIPT" ]; then
      bash "$ENSURE_SCRIPT" --symbols "$SYMBOLS" --config "$CONFIG_FILE" --quick_windows 2 --data_root "data/derived" || \
        echo "WARN ensure_quick_data failed; continuing with existing local data."
    else
      echo "WARN ensure script not found: $ENSURE_SCRIPT"
    fi
  fi
else
  SYMBOLS="${SYMBOLS_OVERRIDE:-BTCUSDT,ETHUSDT,BNBUSDT}"
fi

WINDOWS_TOTAL="$(echo "$WINDOWS_JSON" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")"
WINDOWS_COMPLETED=0
WINDOWS_FAILED=0

while IFS='|' read -r W_NAME W_START W_END; do
  echo ""
  echo "----------------------------------------------------------------"
  echo "Processing Window: $W_NAME ($W_START to $W_END)"
  echo "----------------------------------------------------------------"

  CMD=(bash "$RUNNER_SCRIPT" --symbols "$SYMBOLS" --start "$W_START" --end "$W_END" --strategy vwap_supertrend --mode foreground)
  PIPE_OUT="$("${CMD[@]}" 2>&1)"
  EXIT_CODE=$?
  if [ -n "$PIPE_OUT" ]; then
    echo "$PIPE_OUT"
  fi

  RUN_OUT_DIR="$(echo "$PIPE_OUT" | grep "OUT_DIR:" | tail -n1 | awk '{print $2}' | tr -d '[:space:]')"
  LOG_PATH="$(echo "$PIPE_OUT" | grep "^LOG:" | tail -n1 | awk '{print $2}' | tr -d '[:space:]')"
  [ -n "$LOG_PATH" ] || LOG_PATH="NA"
  [ -n "$RUN_OUT_DIR" ] || RUN_OUT_DIR="NA"
  RERUN_CMD="bash $RUNNER_SCRIPT --symbols \"$SYMBOLS\" --start \"$W_START\" --end \"$W_END\" --strategy vwap_supertrend --mode foreground"

  if [[ $EXIT_CODE -ne 0 && $EXIT_CODE -ne 2 ]]; then
    REASON_CODE="$(classify_failure_reason "$PIPE_OUT" "$EXIT_CODE")"
    REASON="${REASON_CODE};exit=${EXIT_CODE};log=${LOG_PATH};out_dir=${RUN_OUT_DIR}"
    REASON="$(sanitize_field "$REASON")"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
      "$W_NAME" "$W_START" "$W_END" "ERROR" "$RUN_OUT_DIR" "UNKNOWN" "UNKNOWN" "$REASON" "$SYMBOLS" >> "$RESULTS_TSV"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
      "$W_NAME" "$REASON_CODE" "$EXIT_CODE" "$LOG_PATH" "$RUN_OUT_DIR" "$SYMBOLS" "$RERUN_CMD" >> "$DIAG_TSV"
    WINDOWS_FAILED=$((WINDOWS_FAILED + 1))
    continue
  fi

  if [ "$RUN_OUT_DIR" = "NA" ] || [ ! -d "$RUN_OUT_DIR" ]; then
    REASON="missing_out_dir"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
      "$W_NAME" "MISSING_OUT_DIR" "$EXIT_CODE" "$LOG_PATH" "$RUN_OUT_DIR" "$SYMBOLS" "$RERUN_CMD" >> "$DIAG_TSV"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
      "$W_NAME" "$W_START" "$W_END" "ERROR" "$RUN_OUT_DIR" "UNKNOWN" "UNKNOWN" "$REASON" "$SYMBOLS" >> "$RESULTS_TSV"
    WINDOWS_FAILED=$((WINDOWS_FAILED + 1))
    continue
  fi

  META_PATH="$RUN_OUT_DIR/window_meta.json"
  cat <<EOF > "$META_PATH"
{
  "window_name": "$W_NAME",
  "start": "$W_START",
  "end": "$W_END",
  "symbols": "$SYMBOLS",
  "run_id": "$RUN_ID",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

  GATE_STATUS="UNKNOWN"
  if [ -f "$RUN_OUT_DIR/gate.json" ]; then
    GATE_PASS="$(python3 -c "import json; print(json.load(open('$RUN_OUT_DIR/gate.json')).get('results', {}).get('overall', {}).get('pass'))" 2>/dev/null || echo "None")"
    if [ "$GATE_PASS" = "True" ]; then
      GATE_STATUS="PASS"
    elif [ "$GATE_PASS" = "False" ]; then
      GATE_STATUS="FAIL"
    fi
  fi

  DECISION="UNKNOWN"
  if [ -f "$RUN_OUT_DIR/selection.json" ]; then
    DECISION="$(python3 -c "import json; print(json.load(open('$RUN_OUT_DIR/selection.json')).get('decision', 'UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$W_NAME" "$W_START" "$W_END" "COMPLETED" "$RUN_OUT_DIR" "$GATE_STATUS" "$DECISION" "-" "$SYMBOLS" >> "$RESULTS_TSV"
  WINDOWS_COMPLETED=$((WINDOWS_COMPLETED + 1))
  echo "Window $W_NAME Completed. Gate: $GATE_STATUS | Decision: $DECISION"
done < <(echo "$WINDOWS_JSON" | python3 -c "import sys, json; [print(f\"{w['name']}|{w['start']}|{w['end']}\") for w in json.load(sys.stdin)]")

echo ""
echo "=== Generating Walk-Forward Report ==="
python3 scripts/report_walkforward.py \
  --config "$CONFIG_FILE" \
  --reports_dir "$REPORTS_DIR" \
  --run_id "$RUN_ID" \
  --suite_results_tsv "$RESULTS_TSV" \
  --suite_mode "$( [ "$QUICK_MODE" = true ] && echo QUICK || echo FULL_SUITE )"
REPORT_RC=$?
if [ $REPORT_RC -ne 0 ]; then
  echo "Error: report generation failed for run_id=$RUN_ID"
  exit $REPORT_RC
fi

RUN_REPORT_JSON="$WF_RUN_DIR/walkforward.json"
LATEST_UPDATED="$(python3 -c "import json; print(json.load(open('$RUN_REPORT_JSON')).get('latest_updated', False))" 2>/dev/null || echo "False")"
if [ "$LATEST_UPDATED" = "True" ]; then
  LATEST_JSON_PATH="$(python3 -c "import json; print(json.load(open('$RUN_REPORT_JSON')).get('latest_update_path', 'reports/walkforward_latest.json'))" 2>/dev/null || echo "reports/walkforward_latest.json")"
  echo "LATEST_UPDATED run_id=$RUN_ID latest_json=$LATEST_JSON_PATH"
  echo "=== Generating Action Items ==="
  python3 scripts/generate_action_items.py --reports_dir "$REPORTS_DIR" --data_dir "$DATA_ROOT"
else
  LATEST_REASON="$(python3 -c "import json; print(json.load(open('$RUN_REPORT_JSON')).get('latest_warning_reason', 'LATEST_NOT_UPDATED_STALE_RISK'))" 2>/dev/null || echo "LATEST_NOT_UPDATED_STALE_RISK")"
  echo "=== Skipping Action Items ==="
  echo "WARN reason=$LATEST_REASON run_id=$RUN_ID run_dir=$WF_RUN_DIR"
fi

echo "Summary: completed=$WINDOWS_COMPLETED failed=$WINDOWS_FAILED total=$WINDOWS_TOTAL run_id=$RUN_ID"
if [ -s "$DIAG_TSV" ]; then
  python3 - "$DIAG_TSV" "$WF_RUN_DIR/failure_diagnostics.json" "$WF_RUN_DIR/failure_diagnostics.md" "$CONFIG_FILE" "$QUICK_MODE" <<'PY'
import json
import sys
from pathlib import Path

tsv_path = Path(sys.argv[1])
json_path = Path(sys.argv[2])
md_path = Path(sys.argv[3])
config_path = Path(sys.argv[4])
quick_mode = sys.argv[5].lower() == "true"
local_cache_path = str(Path("data/backtests").resolve())
windows_cfg = {}
if config_path.exists():
    try:
        for w in json.loads(config_path.read_text(encoding="utf-8")):
            if isinstance(w, dict) and w.get("name"):
                windows_cfg[w["name"]] = w
    except Exception:
        windows_cfg = {}
rows = []
for raw in tsv_path.read_text(encoding="utf-8").splitlines():
    if not raw.strip():
        continue
    parts = raw.split("\t")
    if len(parts) != 7:
        continue
    window_name = parts[0]
    cfg = windows_cfg.get(window_name, {})
    rows.append(
        {
            "window": window_name,
            "reason_code": parts[1],
            "exit_code": parts[2],
            "log_path": parts[3],
            "run_out_dir": parts[4],
            "symbols": parts[5],
            "rerun_command": parts[6],
            "required_start": cfg.get("start"),
            "required_end": cfg.get("end"),
            "local_cache_path_checked": local_cache_path,
        }
    )

insufficient_codes = {"INSUFFICIENT_DATA_RESAMPLE", "NO_DATA_IN_RANGE", "NO_BACKTEST_RESULTS"}
all_insufficient = bool(rows) and all(r.get("reason_code") in insufficient_codes for r in rows)
diag_reason = "QUICK_SKIPPED_INSUFFICIENT_LOCAL_DATA" if quick_mode and all_insufficient else "WINDOW_FAILURES_PRESENT"
remediation_cmd = "bash scripts/smoke_backtest.sh"
json_path.write_text(
    json.dumps(
        {
            "run_mode": "QUICK" if quick_mode else "FULL_SUITE",
            "reason_token": diag_reason,
            "local_cache_path_checked": local_cache_path,
            "remediation": {
                "note": "manual backfill required" if diag_reason == "QUICK_SKIPPED_INSUFFICIENT_LOCAL_DATA" else "inspect per-window failures",
                "commands": [
                    remediation_cmd,
                    "bash scripts/walkforward_suite.sh --quick --symbols BTCUSDT",
                ],
            },
            "failures": rows,
        },
        indent=2,
    ),
    encoding="utf-8",
)
lines = [
    "# Walkforward Failure Diagnostics",
    "",
    f"- reason_token: {diag_reason}",
    f"- run_mode: {'QUICK' if quick_mode else 'FULL_SUITE'}",
    f"- local_cache_path_checked: {local_cache_path}",
    "",
    "| window | reason_code | exit_code | log_path | run_out_dir |",
    "|---|---|---|---|---|",
]
for row in rows:
    lines.append(
        f"| {row['window']} | {row['reason_code']} | {row['exit_code']} | "
        f"{row['log_path']} | {row['run_out_dir']} |"
    )
lines.append("")
lines.append("## Reproduce Commands")
for row in rows:
    lines.append(f"- `{row['window']}`: `{row['rerun_command']}`")
lines.append("")
lines.append("## Suggested Remediation")
lines.append(f"- `{remediation_cmd}`")
lines.append("- `bash scripts/walkforward_suite.sh --quick --symbols BTCUSDT`")
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"FAILURE_DIAGNOSTICS json={json_path} md={md_path}")
PY
fi
if [ "$WINDOWS_COMPLETED" -ne "$WINDOWS_TOTAL" ] || [ "$WINDOWS_FAILED" -gt 0 ]; then
  exit 1
fi

echo "Done."
exit 0
