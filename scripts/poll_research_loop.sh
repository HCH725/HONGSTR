#!/usr/bin/env bash
# HONGSTR Research Poller v1
# Runs every 30 min via launchd (com.hongstr.research_poller).
# If trigger_queue.jsonl has pending events → runs research loop once.
# If no pending events → exits immediately (no-op).
# ALWAYS exits 0. Never blocks ETL / dashboard / tg_cp.
#
# Atomic lock: mkdir data/state/_research/.poller.lock
# (mkdir is atomic on APFS/HFS+; no flock needed)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Load .env ──────────────────────────────────────────────────────────────────
if [[ -f "${REPO_ROOT}/scripts/load_env.sh" ]]; then
  # shellcheck disable=SC1090
  source "${REPO_ROOT}/scripts/load_env.sh" || true
elif [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${REPO_ROOT}/.env" || true
  set +a
fi

export PYTHONPATH="${REPO_ROOT}"

# ── Paths ──────────────────────────────────────────────────────────────────────
STATE_DIR="${REPO_ROOT}/data/state/_research"
LOCK_DIR="${STATE_DIR}/.poller.lock"
QUEUE_PY="${REPO_ROOT}/research/loop/trigger_queue.py"
POLLER_STATE="${STATE_DIR}/poller_last.json"
PYTHON="${REPO_ROOT}/.venv/bin/python"
TS_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

mkdir -p "${STATE_DIR}"

# ── Logging helper ────────────────────────────────────────────────────────────
log() { echo "[poller] ${TS_UTC} $*"; }

# ── Ensure we always exit 0 and release lock ─────────────────────────────────
_cleanup() {
  rmdir "${LOCK_DIR}" 2>/dev/null || true
}
trap '_cleanup' EXIT

# ── Acquire atomic lock ───────────────────────────────────────────────────────
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  log "Already running (lock held). Skipping."
  exit 0
fi
log "Lock acquired."

# ── Check pending triggers ────────────────────────────────────────────────────
# Then check cooldown
COOLDOWN_SEC="${HONGSTR_RESEARCH_POLLER_COOLDOWN_SEC:-600}"
DEDUPE_SEC="${HONGSTR_RESEARCH_TRIGGER_DEDUPE_SEC:-3600}"
export HONGSTR_RESEARCH_TRIGGER_DEDUPE_SEC="${DEDUPE_SEC}"
NOW_EPOCH="$(date +%s)"

# Load last loop ts
LAST_LOOP_TS="$(cat "${POLLER_STATE}" 2>/dev/null | "${PYTHON}" -c "import sys, json; print(json.load(sys.stdin).get('last_loop_ts_utc', ''))" 2>/dev/null || echo "")"
LAST_LOOP_EPOCH=0
if [[ -n "${LAST_LOOP_TS}" ]]; then
  # Compatibility: convert ISO to epoch
  LAST_LOOP_EPOCH="$(python3 -c "import datetime; print(int(datetime.datetime.fromisoformat('${LAST_LOOP_TS}'.replace('Z','+00:00')).timestamp()))" 2>/dev/null || echo 0)"
fi

ELAPSED=$((NOW_EPOCH - LAST_LOOP_EPOCH))

PENDING="$("${PYTHON}" - <<'PY'
import sys
sys.path.insert(0, ".")
from research.loop.trigger_queue import peek_pending
print("1" if peek_pending() else "0")
PY
2>/dev/null || echo "0")"

if [[ "${PENDING}" != "1" ]]; then
  log "No pending triggers. Exiting early."
  # Keep last_loop_ts_utc
  cat > "${POLLER_STATE}.tmp" <<JSON
{"ts_utc":"${TS_UTC}","triggered":false,"status":"idle","error":null,"last_loop_ts_utc":"${LAST_LOOP_TS}"}
JSON
  mv "${POLLER_STATE}.tmp" "${POLLER_STATE}"
  exit 0
fi

if [[ ${ELAPSED} -lt ${COOLDOWN_SEC} ]]; then
  log "Cooldown active (${ELAPSED}s < ${COOLDOWN_SEC}s). Skipping loop but keeping triggers."
  cat > "${POLLER_STATE}.tmp" <<JSON
{"ts_utc":"${TS_UTC}","triggered":false,"status":"cooldown_skip","error":null,"last_loop_ts_utc":"${LAST_LOOP_TS}"}
JSON
  mv "${POLLER_STATE}.tmp" "${POLLER_STATE}"
  exit 0
fi

# ── Run research loop ─────────────────────────────────────────────────────────
log "Pending trigger found & cooldown passed → running research loop..."
LOOP_STATUS="ok"
if ! bash "${REPO_ROOT}/scripts/run_research_loop.sh" --once; then
  log "Research loop returned non-zero (stability wrapper should avoid this)."
  LOOP_STATUS="warn"
fi

# ── Mark queue as drained ─────────────────────────────────────────────────────
"${PYTHON}" - <<'PY' || true
import sys; sys.path.insert(0, ".")
from research.loop.trigger_queue import mark_drained
mark_drained()
PY

# ── Write poller state ────────────────────────────────────────────────────────
LOOP_FINISHED_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "${POLLER_STATE}.tmp" <<JSON
{"ts_utc":"${TS_UTC}","triggered":true,"status":"${LOOP_STATUS}","error":null,"last_loop_ts_utc":"${LOOP_FINISHED_TS}"}
JSON
mv "${POLLER_STATE}.tmp" "${POLLER_STATE}"

log "Poller done (loop_status=${LOOP_STATUS})."
exit 0
