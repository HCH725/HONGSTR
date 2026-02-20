#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f "${REPO_ROOT}/scripts/load_env.sh" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/scripts/load_env.sh" || true
else
  echo "WARN: scripts/load_env.sh not found; continue with current env" >&2
fi

echo "TG_BOT_TOKEN_SET=$([ -n "${TG_BOT_TOKEN:-}" ] && echo 1 || echo 0)"
echo "TG_CHAT_ID_SET=$([ -n "${TG_CHAT_ID:-}" ] && echo 1 || echo 0)"
echo "TG_PARSE_MODE=${TG_PARSE_MODE:-}"

curl -I --max-time 5 https://api.telegram.org >/tmp/hongstr_tg_sanity_curl_head.txt 2>&1 || true
if rg -q "Could not resolve host|timed out|Failed to connect|curl: \\(" /tmp/hongstr_tg_sanity_curl_head.txt; then
  echo "WARN: Telegram endpoint precheck failed"
fi
tail -n 3 /tmp/hongstr_tg_sanity_curl_head.txt || true

notify_out="$(bash scripts/notify_telegram.sh \
  --title "HONGSTR TG sanity" \
  --status "INFO" \
  --body "ping $(hostname) $(date)" 2>&1 || true)"
echo "$notify_out"

if echo "$notify_out" | rg -q "INFO: Telegram sendMessage ok"; then
  echo "TG_SANITY=OK"
else
  echo "TG_SANITY=WARN"
fi

exit 0
