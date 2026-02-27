#!/bin/bash
# scripts/pm_snapshot.sh
# Idempotent system health and strategy audit for HONGSTR PM.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "== [1/5] Repository Refresh =="
git checkout main
git pull --ff-only

echo "== [2/5] Refreshing State =="
bash scripts/refresh_state.sh

echo "== [3/5] HealthPack Summary =="
./.venv/bin/python - <<'PY'
import json
import os
path = "data/state/system_health_latest.json"
if os.path.exists(path):
    d = json.load(open(path))
    print(f"generated_utc: {d.get('generated_utc')}")
    print(f"ssot_status:   {d.get('ssot_status')}")
    components = d.get('components', {})
    print("components:")
    for k, v in components.items():
        status = v.get('status') if isinstance(v, dict) else v
        print(f"  - {k:15}: {status}")
else:
    print(f"ERROR: {path} not found.")
PY

echo "== [4/5] Latest Backtest Artifacts =="
find data/backtests -maxdepth 3 -type f -name "summary.json" | tail -n 3 | while read p; do
    dir=$(dirname "$p")
    bt_id=$(basename "$dir")
    echo "- BT: $bt_id"
    if [ -f "$dir/gate.json" ]; then 
        echo "  - Gate: $(./.venv/bin/python -c 'import json; print(json.load(open("'$dir'/gate.json")).get("ssot_status", "N/A"))')"
    fi
    ./.venv/bin/python -c 'import json; d=json.load(open("'$p'")); print("  - Sharpe: " + str(d.get("sharpe", "N/A")))'
done

echo "== [5/5] Strategy Pool Snapshots =="
ls -lah data/state/strategy_pool.json data/state/strategy_pool_summary.json data/state/_research/leaderboard.json 2>/dev/null || true

echo "== [Guardrails] Running Preflight Status =="

# 1. Smoke Tests
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py

# 2. Core Diff Guard
CORE_DIFF=$(git diff origin/main...HEAD -- src/hongstr | wc -l | tr -d '[:space:]')
if [ "$CORE_DIFF" -gt 0 ]; then
    echo "ERROR: Forbidden core diff detected in src/hongstr/ ($CORE_DIFF lines)"
    exit 1
fi

# 3. tg_cp No-Exec Guard
EXEC_CALLS=$(rg 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py | wc -l | tr -d '[:space:]' || echo 0)
if [ "$EXEC_CALLS" -gt 0 ]; then
    echo "ERROR: Forbidden exec calls detected in tg_cp_server.py ($EXEC_CALLS calls)"
    exit 1
fi

# 4. Data Staged Guard
DATA_STAGED=$(git status --porcelain | grep '^.. data/' | wc -l | tr -d '[:space:]' || echo 0)
if [ "$DATA_STAGED" -gt 0 ]; then
    echo "ERROR: Forbidden data/ artifacts staged or untracked ($DATA_STAGED files)"
    exit 1
fi

echo "OK: PM snapshot done."
