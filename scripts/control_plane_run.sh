#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

source scripts/load_env.sh || true

PY="${PY:-$REPO_ROOT/.venv/bin/python}"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3 || true)"
fi
if [[ -z "$PY" ]]; then
  echo "WARN: no python interpreter; skip control-plane run" >&2
  exit 0
fi

EVENT_FILE="data/events/latest_event.json"
REPORT_JSON="reports/control_plane_latest.json"
REPORT_MD="reports/control_plane_latest.md"

set +e
"$PY" scripts/event_router.py --repo-root "$REPO_ROOT" --output "$EVENT_FILE" >/tmp/hongstr_event_router.log 2>&1
router_rc=$?
PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}" "$PY" -m hongstr.control_plane.runner \
  --event-file "$EVENT_FILE" \
  --output-json "$REPORT_JSON" \
  --output-md "$REPORT_MD" >/tmp/hongstr_control_plane_runner.log 2>&1
runner_rc=$?
set -e

status="FAIL"
if [[ -f "$REPORT_JSON" ]]; then
  status="$($PY - <<'PY'
import json
from pathlib import Path
p=Path('reports/control_plane_latest.json')
try:
    d=json.loads(p.read_text(encoding='utf-8'))
    print(str(d.get('status','FAIL')))
except Exception:
    print('FAIL')
PY
)"
fi

if [[ "$status" = "FAIL" && -x scripts/notify_telegram.sh ]]; then
  bash scripts/notify_telegram.sh \
    --title "HONGSTR Control Plane" \
    --status warn \
    --body "control-plane status=FAIL (router_rc=${router_rc}, runner_rc=${runner_rc})" \
    --log-tail /tmp/hongstr_control_plane_runner.log \
    --tail-lines 80 || true
fi

echo "CONTROL_PLANE_STATUS=${status}"
echo "CONTROL_PLANE_EVENT=${EVENT_FILE}"
echo "CONTROL_PLANE_REPORT_JSON=${REPORT_JSON}"
echo "CONTROL_PLANE_REPORT_MD=${REPORT_MD}"
exit 0
