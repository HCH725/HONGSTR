#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPORT_JSON=""
RUN_ID=""
SYMBOLS_OVERRIDE=""
CONFIG_FILE="configs/windows.json"
RUNNER_SCRIPT="scripts/run_and_verify.sh"
REPORTS_DIR="reports"
DRY_RUN=0

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
  echo "pipeline_exit_${exit_code}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --report_json)
      REPORT_JSON="${2:-}"
      shift 2
      ;;
    --run_id)
      RUN_ID="${2:-}"
      shift 2
      ;;
    --symbols)
      SYMBOLS_OVERRIDE="${2:-}"
      shift 2
      ;;
    --config)
      CONFIG_FILE="${2:-}"
      shift 2
      ;;
    --runner_script)
      RUNNER_SCRIPT="${2:-}"
      shift 2
      ;;
    --reports_dir)
      REPORTS_DIR="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -n "$RUN_ID" ] && [ -z "$REPORT_JSON" ]; then
  REPORT_JSON="${REPORTS_DIR}/walkforward/${RUN_ID}/walkforward.json"
fi

if [ -z "$REPORT_JSON" ]; then
  REPORT_JSON="$(python3 - "$REPORTS_DIR" "$CONFIG_FILE" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]) / "walkforward"
config_path = Path(sys.argv[2])
candidates = [p / "walkforward.json" for p in root.glob("*/") if (p / "walkforward.json").exists()]
if not candidates:
    raise SystemExit(1)

expected_total = None
try:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if isinstance(cfg, list):
        expected_total = len(cfg)
except Exception:
    expected_total = None

candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
best_full = None
best_full_failed = -1
best_any = None
best_any_failed = -1
for c in candidates:
    name = c.parent.name
    if (
        name.startswith("unit_")
        or name.startswith("test_")
        or name.endswith("_src")
    ):
        continue
    try:
        payload = json.loads(c.read_text(encoding="utf-8"))
    except Exception:
        continue
    run_mode = str(payload.get("run_mode", "")).upper()
    total = payload.get("windows_total")
    if not isinstance(total, int):
        total = len(payload.get("windows") or [])
    failed_count = len(payload.get("failed_windows_summary") or [])
    if failed_count > best_any_failed:
        best_any = c
        best_any_failed = failed_count
    full_total_match = expected_total is None or total == expected_total
    if run_mode == "FULL" and full_total_match and failed_count > best_full_failed:
        best_full = c
        best_full_failed = failed_count

if best_full is not None and best_full_failed > 0:
    print(best_full)
    raise SystemExit(0)
if best_any is not None and best_any_failed > 0:
    print(best_any)
    raise SystemExit(0)
for c in candidates:
    name = c.parent.name
    if not (
        name.startswith("unit_")
        or name.startswith("test_")
        or name.endswith("_src")
    ):
        print(c)
        raise SystemExit(0)
print(candidates[0])
PY
)" || {
    echo "Error: no walkforward report found. Use --report_json." >&2
    exit 1
  }
fi

if [ ! -f "$REPORT_JSON" ]; then
  echo "Error: report_json not found: $REPORT_JSON" >&2
  exit 1
fi

PARSED="$(python3 - "$REPORT_JSON" "$SYMBOLS_OVERRIDE" "$CONFIG_FILE" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
symbols_override = sys.argv[2].strip()
config_path = Path(sys.argv[3])
payload = json.loads(report_path.read_text(encoding="utf-8"))
run_id = payload.get("run_id", "")
windows = {w.get("name"): w for w in payload.get("windows", [])}
windows_total = len(payload.get("windows", []))
cfg_windows = {}
if config_path.exists():
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        cfg_windows = {w.get("name"): w for w in cfg if isinstance(w, dict)}
    except Exception:
        cfg_windows = {}

failed = []
for item in payload.get("failed_windows_summary", []):
    if isinstance(item, dict):
        name = item.get("name")
    else:
        name = str(item)
    if not name:
        continue
    window = windows.get(name, {})
    cfg_window = cfg_windows.get(name, {})
    start = cfg_window.get("start") or window.get("start", "")
    end = cfg_window.get("end") or window.get("end", "")
    symbols = symbols_override or ",".join(window.get("symbols") or ["BTCUSDT"])
    failed.append((name, start, end, symbols))

print(f"RUN_ID\t{run_id}")
print(f"REPORT\t{report_path}")
print(f"TOTAL_WINDOWS\t{windows_total}")
print(f"FAILED_COUNT\t{len(failed)}")
for name, start, end, symbols in failed:
    print(f"WINDOW\t{name}\t{start}\t{end}\t{symbols}")
PY
)"

echo "$PARSED"

FAILED_COUNT="$(awk -F'\t' '$1=="FAILED_COUNT"{print $2}' <<<"$PARSED")"
TOTAL_WINDOWS="$(awk -F'\t' '$1=="TOTAL_WINDOWS"{print $2}' <<<"$PARSED")"
if [ -z "$FAILED_COUNT" ] || [ "$FAILED_COUNT" = "0" ]; then
  echo "No failed windows to rerun."
  exit 0
fi

BASE_RUN_ID="$(awk -F'\t' '$1=="RUN_ID"{print $2}' <<<"$PARSED")"
if [ -z "$BASE_RUN_ID" ]; then
  BASE_RUN_ID="unknown"
fi

RERUN_RUN_ID="$(date -u +%Y%m%d_%H%M%S)_$(git rev-parse --short HEAD 2>/dev/null || echo nogit)_rerun"
WF_RUN_DIR="${REPORTS_DIR}/walkforward/${RERUN_RUN_ID}"
RESULTS_TSV="${WF_RUN_DIR}/suite_results.tsv"
COMMANDS_TSV="${WF_RUN_DIR}/rerun_commands.tsv"

mkdir -p "$WF_RUN_DIR"
: > "$RESULTS_TSV"
: > "$COMMANDS_TSV"

COMMAND_COUNT=0
while IFS=$'\t' read -r tag w_name w_start w_end w_symbols; do
  [ "$tag" = "WINDOW" ] || continue
  CMD=(bash "$RUNNER_SCRIPT" --symbols "$w_symbols" --start "$w_start" --end "$w_end" --strategy vwap_supertrend --mode foreground)
  CMD_STR="${CMD[*]}"
  printf "%s\t%s\t%s\t%s\n" "$w_name" "$w_start" "$w_end" "$(sanitize_field "$CMD_STR")" >> "$COMMANDS_TSV"
  COMMAND_COUNT=$((COMMAND_COUNT + 1))
  if [ "$DRY_RUN" = "1" ]; then
    echo "[DRY-RUN] ${CMD_STR}"
    continue
  fi

  PIPE_OUT="$("${CMD[@]}" 2>&1)"
  EXIT_CODE=$?
  [ -n "$PIPE_OUT" ] && echo "$PIPE_OUT"
  RUN_OUT_DIR="$(echo "$PIPE_OUT" | grep "OUT_DIR:" | tail -n1 | awk '{print $2}' | tr -d '[:space:]')"
  LOG_PATH="$(echo "$PIPE_OUT" | grep "^LOG:" | tail -n1 | awk '{print $2}' | tr -d '[:space:]')"
  [ -n "$LOG_PATH" ] || LOG_PATH="NA"
  [ -n "$RUN_OUT_DIR" ] || RUN_OUT_DIR="NA"

  if [[ $EXIT_CODE -ne 0 && $EXIT_CODE -ne 2 ]]; then
    REASON_CODE="$(classify_failure_reason "$PIPE_OUT" "$EXIT_CODE")"
    REASON_DETAIL="${REASON_CODE};exit=${EXIT_CODE};log=${LOG_PATH};out_dir=${RUN_OUT_DIR}"
    REASON_DETAIL="$(sanitize_field "$REASON_DETAIL")"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
      "$w_name" "$w_start" "$w_end" "ERROR" "$RUN_OUT_DIR" "UNKNOWN" "UNKNOWN" "$REASON_DETAIL" "$w_symbols" >> "$RESULTS_TSV"
    continue
  fi

  if [ "$RUN_OUT_DIR" = "NA" ] || [ ! -d "$RUN_OUT_DIR" ]; then
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
      "$w_name" "$w_start" "$w_end" "ERROR" "$RUN_OUT_DIR" "UNKNOWN" "UNKNOWN" "MISSING_OUT_DIR;exit=${EXIT_CODE};log=${LOG_PATH}" "$w_symbols" >> "$RESULTS_TSV"
    continue
  fi

  GATE_STATUS="UNKNOWN"
  if [ -f "$RUN_OUT_DIR/gate.json" ]; then
    GATE_PASS="$(python3 -c "import json; print(json.load(open('$RUN_OUT_DIR/gate.json')).get('results', {}).get('overall', {}).get('pass'))" 2>/dev/null || echo None)"
    if [ "$GATE_PASS" = "True" ]; then
      GATE_STATUS="PASS"
    elif [ "$GATE_PASS" = "False" ]; then
      GATE_STATUS="FAIL"
    fi
  fi

  DECISION="UNKNOWN"
  if [ -f "$RUN_OUT_DIR/selection.json" ]; then
    DECISION="$(python3 -c "import json; print(json.load(open('$RUN_OUT_DIR/selection.json')).get('decision', 'UNKNOWN'))" 2>/dev/null || echo UNKNOWN)"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$w_name" "$w_start" "$w_end" "COMPLETED" "$RUN_OUT_DIR" "$GATE_STATUS" "$DECISION" "-" "$w_symbols" >> "$RESULTS_TSV"
done <<<"$PARSED"

echo "RERUN_SUMMARY base_run_id=${BASE_RUN_ID} rerun_run_id=${RERUN_RUN_ID} failed_windows=${FAILED_COUNT} commands=${COMMAND_COUNT}"
echo "RERUN_SELECTION total_windows=${TOTAL_WINDOWS:-unknown} selected_failed_windows=${FAILED_COUNT}"

if [ "$DRY_RUN" = "1" ]; then
  exit 0
fi

python3 scripts/report_walkforward.py \
  --config "$CONFIG_FILE" \
  --reports_dir "$REPORTS_DIR" \
  --run_id "$RERUN_RUN_ID" \
  --suite_results_tsv "$RESULTS_TSV" \
  --no_latest_update \
  --suite_mode RERUN_SELECTED
REPORT_RC=$?
if [ $REPORT_RC -ne 0 ]; then
  echo "Error: failed to regenerate walkforward report for rerun run_id=${RERUN_RUN_ID}" >&2
  exit $REPORT_RC
fi

python3 - "$RERUN_RUN_ID" "$BASE_RUN_ID" "$FAILED_COUNT" "$REPORTS_DIR" "$REPORT_JSON" "$COMMANDS_TSV" <<'PY'
import json
from datetime import datetime
from pathlib import Path
import sys

run_id = sys.argv[1]
base_run_id = sys.argv[2]
failed_count = int(sys.argv[3]) if sys.argv[3].isdigit() else 0
reports_dir = Path(sys.argv[4])
base_report_path = Path(sys.argv[5])
commands_tsv = Path(sys.argv[6])
run_report_path = reports_dir / "walkforward" / run_id / "walkforward.json"
run_report = json.loads(run_report_path.read_text(encoding="utf-8"))
base_report = json.loads(base_report_path.read_text(encoding="utf-8")) if base_report_path.exists() else {}

commands = []
if commands_tsv.exists():
    for raw in commands_tsv.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 4:
            continue
        commands.append(
            {
                "window": parts[0],
                "start": parts[1],
                "end": parts[2],
                "command": parts[3],
            }
        )

payload = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "run_id": run_id,
    "base_run_id": base_run_id,
    "run_mode": "RERUN",
    "rerun_scope": "FAILED_ONLY",
    "latest_pointers_updated": False,
    "latest_pointer_policy_reason": "RERUN_NEVER_UPDATES_LATEST_BY_POLICY",
    "completed": run_report.get("windows_completed", 0),
    "total": run_report.get("windows_total", 0),
    "windows_selected": failed_count,
    "windows_total": run_report.get("windows_total", 0),
    "failed": run_report.get("windows_failed", 0),
    "selected_failed_windows": failed_count,
    "status": run_report.get("status", "UNKNOWN"),
    "windows": [
        {
            "name": w.get("name"),
            "status": w.get("status"),
            "error": w.get("error"),
            "run_dir": w.get("run_dir"),
        }
        for w in run_report.get("windows", [])
    ],
    "failed_windows": run_report.get("failed_windows_summary", []),
    "base_failed_windows": base_report.get("failed_windows_summary", []),
    "rerun_commands": commands,
    "walkforward_run_report": str(run_report_path),
}

selected_names = [c["window"] for c in commands]
selected_set = set(selected_names)
selected_windows = [w for w in payload["windows"] if w.get("name") in selected_set]
payload["selected_completed"] = sum(1 for w in selected_windows if w.get("status") == "COMPLETED")
payload["selected_failed"] = sum(1 for w in selected_windows if w.get("status") in {"FAILED", "ERROR"})
payload["selected_total"] = len(selected_windows)

json_path = reports_dir / "walkforward_rerun_latest.json"
md_path = reports_dir / "walkforward_rerun_latest.md"
json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

lines = [
    "# Walkforward Rerun Latest",
    "",
    f"## RERUN MODE: FAILED_ONLY — PARTIAL ({payload['completed']}/{payload['total']}) is expected",
    "",
    f"- generated_at: {payload['generated_at']}",
    f"- run_id: {payload['run_id']}",
    f"- base_run_id: {payload['base_run_id']}",
    f"- run_mode: {payload['run_mode']}",
    f"- rerun_scope: {payload['rerun_scope']}",
    f"- status: {payload['status']}",
    f"- completed: {payload['completed']}",
    f"- total: {payload['total']}",
    f"- windows_selected: {payload['windows_selected']}",
    f"- windows_total: {payload['windows_total']}",
    f"- failed: {payload['failed']}",
    f"- selected_failed_windows: {payload['selected_failed_windows']}",
    f"- selected_completed: {payload['selected_completed']}",
    f"- selected_failed: {payload['selected_failed']}",
    f"- selected_total: {payload['selected_total']}",
    f"- latest_pointers_updated: {payload['latest_pointers_updated']}",
    f"- latest_pointer_policy_reason: {payload['latest_pointer_policy_reason']}",
    f"- walkforward_run_report: {payload['walkforward_run_report']}",
    "",
    "## Windows",
    "| name | status | error |",
    "|---|---|---|",
]
for item in payload["windows"]:
    lines.append(f"| {item.get('name')} | {item.get('status')} | {item.get('error') or '-'} |")
lines += [
    "",
    "## Base Failed Windows (from source report)",
]
base_failed = payload.get("base_failed_windows") or []
if base_failed:
    lines.append("| name | status | error |")
    lines.append("|---|---|---|")
    for item in base_failed:
        lines.append(
            f"| {item.get('name', '-')} | {item.get('status', '-')} | {item.get('error', '-') or '-'} |"
        )
else:
    lines.append("- none")

lines += [
    "",
    "## Skipped Windows",
    "Skipped windows are expected in FAILED_ONLY rerun mode when a window is not in `failed_windows_summary`.",
]
skipped = [w for w in payload["windows"] if w.get("status") == "PENDING"]
if skipped:
    lines.append("| name | reason |")
    lines.append("|---|---|")
    for item in skipped:
        lines.append(f"| {item.get('name')} | SKIP: not in failed_windows_summary |")
else:
    lines.append("- none")

lines += [
    "",
    "## Reproduce Commands",
]
if commands:
    for item in commands:
        lines.append(f"- `{item.get('window')}`: `{item.get('command')}`")
else:
    lines.append("- none")
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"RERUN_LATEST updated json={json_path} md={md_path}")
PY

echo "Rerun complete. Reports: ${REPORTS_DIR}/walkforward/${RERUN_RUN_ID}/"
echo "To refresh full gate summary: bash scripts/gate_all.sh"
