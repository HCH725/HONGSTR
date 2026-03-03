#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

source scripts/load_env.sh || true

REPORT_JSON="reports/control_plane_latest.json"
REPORT_MD="reports/control_plane_latest.md"
RUN_LOG="/tmp/hongstr_control_plane_report.log"

if [[ ! -x "$REPO_ROOT/scripts/control_plane_run.sh" ]]; then
  echo "WARN: control_plane_run.sh not executable; skip control-plane report"
  exit 0
fi

set +e
cp_out="$(bash "$REPO_ROOT/scripts/control_plane_run.sh" 2>&1)"
cp_rc=$?
set -e
printf "%s\n" "$cp_out" > "$RUN_LOG"

status="FAIL"
summary="(missing summary)"
actions_count="0"
llm_mode="unknown"
if [[ -f "$REPORT_JSON" ]]; then
  cp_fields="$(
  python3 - <<'PY'
import json
from pathlib import Path

p = Path("reports/control_plane_latest.json")
data = json.loads(p.read_text(encoding="utf-8"))
status = str(data.get("status", "FAIL"))
summary = str(data.get("summary", "(missing summary)")).replace("\n", " ").strip()
actions = data.get("actions", [])
if not isinstance(actions, list):
    actions = []
llm_mode = str(data.get("llm_mode", "unknown"))
summary = summary.replace("\t", " ")[:200]
print("\t".join([status, str(len(actions)), llm_mode, summary]))
PY
)"
  IFS=$'\t' read -r status actions_count llm_mode summary <<< "$cp_fields"
fi

echo "CONTROL_PLANE_REPORT status=${status} actions=${actions_count} llm_mode=${llm_mode} runner_rc=${cp_rc}"
echo "CONTROL_PLANE_SUMMARY ${summary}"
echo "CONTROL_PLANE_REPORT_JSON=${REPORT_JSON}"
echo "CONTROL_PLANE_REPORT_MD=${REPORT_MD}"

if [[ "${CONTROL_PLANE_REPORT_NOTIFY:-0}" == "1" && -x "$REPO_ROOT/scripts/notify_telegram.sh" ]]; then
  notify_status="$(echo "$status" | tr '[:upper:]' '[:lower:]')"
  bash "$REPO_ROOT/scripts/notify_telegram.sh" \
    --status "${notify_status}" \
    --title "Control Plane Report" \
    --body "status=${status} actions=${actions_count} llm_mode=${llm_mode}\n${summary}" \
    --file "$REPORT_MD" || true
fi

exit 0
