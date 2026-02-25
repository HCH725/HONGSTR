#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load .env (no secrets printed)
source scripts/load_env.sh || true

PY="$REPO_ROOT/.venv/bin/python"
export PY

SYMBOLS="${DAILY_BACKTEST_SYMBOLS:-BTCUSDT ETHUSDT BNBUSDT}"
TIMEFRAMES="${DAILY_BACKTEST_TIMEFRAMES:-1h,4h}"
START_DATE="${DAILY_BACKTEST_START:-2020-01-01}"
END_DATE="${DAILY_BACKTEST_END:-now}"

LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_LOG="$LOG_DIR/daily_backtest_${TS}.out.log"
ERR_LOG="$LOG_DIR/daily_backtest_${TS}.err.log"

notify() {
  if [ -x "$REPO_ROOT/scripts/notify_telegram.sh" ]; then
    bash "$REPO_ROOT/scripts/notify_telegram.sh" "$@" || true
  fi
}

echo "=== Daily Backtest Started: $(date) ===" | tee -a "$OUT_LOG"
echo "symbols=$SYMBOLS timeframes=$TIMEFRAMES start=$START_DATE end=$END_DATE" | tee -a "$OUT_LOG"

# optional: tg sanity (non-blocking)
if [ -x "$REPO_ROOT/scripts/tg_sanity.sh" ]; then
  bash "$REPO_ROOT/scripts/tg_sanity.sh" >>"$OUT_LOG" 2>>"$ERR_LOG" || true
fi

set +e
bash "$REPO_ROOT/scripts/run_and_verify.sh" \
  --mode foreground \
  --no_fail_on_gate \
  --symbols "$SYMBOLS" \
  --timeframes "$TIMEFRAMES" \
  --start "$START_DATE" \
  --end "$END_DATE" >>"$OUT_LOG" 2>>"$ERR_LOG"
RC=$?
set -e

LATEST_RUN_DIR="$(
  awk -F= '/LATEST_RUN_DIR=/{line=$0} END {sub(/^LATEST_RUN_DIR=/, "", line); print line}' "$OUT_LOG"
)"
[ -n "${LATEST_RUN_DIR:-}" ] || LATEST_RUN_DIR="(unknown)"

if [ "$RC" -eq 0 ]; then
  notify --title "HONGSTR Daily Backtest" --status "OK" \
    --body "Daily backtest completed.\nrun_dir: ${LATEST_RUN_DIR}\n$(date)" \
    --log-tail "$OUT_LOG" --tail-lines 40 || true
else
  notify --title "HONGSTR Daily Backtest" --status "WARN" \
    --body "Daily backtest finished with RC=${RC} (gate may fail but artifacts kept).\nrun_dir: ${LATEST_RUN_DIR}\n$(date)" \
    --log-tail "$ERR_LOG" --tail-lines 80 || true
fi

# Enqueue research trigger (stability-first)
PYTHONPATH=. "$REPO_ROOT"/.venv/bin/python -c "from research.loop.trigger_queue import enqueue; import datetime; enqueue({'ts_utc': datetime.datetime.utcnow().isoformat()+'Z','source':'daily_backtest','trigger':'daily_backtest_done'})" || true

echo "=== Daily Backtest Done (RC=$RC) ===" | tee -a "$OUT_LOG"
exit 0
