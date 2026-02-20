#!/usr/bin/env bash
set -euo pipefail

title=""
body=""
status="ok"
link=""
file=""
parse_mode="${TG_PARSE_MODE:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) title="${2:-}"; shift 2 ;;
    --body) body="${2:-}"; shift 2 ;;
    --status) status="${2:-ok}"; shift 2 ;;
    --link) link="${2:-}"; shift 2 ;;
    --file) file="${2:-}"; shift 2 ;;
    *) echo "WARN: unknown arg: $1" >&2; shift ;;
  esac
done

tg_token="${TG_BOT_TOKEN:-}"
tg_chat_id="${TG_CHAT_ID:-}"
if [[ -z "$tg_token" || -z "$tg_chat_id" || "$tg_token" == __TG_* || "$tg_chat_id" == __TG_* ]]; then
  echo "WARN: Telegram disabled (missing TG_BOT_TOKEN/TG_CHAT_ID); skip notify." >&2
  exit 0
fi

host="$(hostname 2>/dev/null || echo unknown-host)"
ts_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
status_upper="$(echo "$status" | tr '[:lower:]' '[:upper:]')"

prefix="[HONGSTR] ${host} ${ts_utc} ${status_upper}"
msg="${prefix}"
if [[ -n "$title" ]]; then
  msg="${msg}\n${title}"
fi
if [[ -n "$body" ]]; then
  msg="${msg}\n${body}"
fi
if [[ -n "$link" ]]; then
  msg="${msg}\n${link}"
fi

api_base="https://api.telegram.org/bot${tg_token}"
send_msg_url="${api_base}/sendMessage"
send_doc_url="${api_base}/sendDocument"

send_message() {
  local resp
  if [[ -n "$parse_mode" ]]; then
    resp="$(curl -sS -X POST "$send_msg_url" \
      --data-urlencode "chat_id=${tg_chat_id}" \
      --data-urlencode "text=${msg}" \
      --data-urlencode "parse_mode=${parse_mode}" \
      2>&1)" || {
      echo "WARN: Telegram sendMessage failed: $resp" >&2
      return 1
    }
  else
    resp="$(curl -sS -X POST "$send_msg_url" \
      --data-urlencode "chat_id=${tg_chat_id}" \
      --data-urlencode "text=${msg}" \
      2>&1)" || {
      echo "WARN: Telegram sendMessage failed: $resp" >&2
      return 1
    }
  fi

  if ! grep -q '"ok":true' <<< "$resp"; then
    echo "WARN: Telegram sendMessage response not ok: $resp" >&2
    return 1
  fi
  return 0
}

send_document() {
  local f="$1"
  [[ -f "$f" ]] || return 0

  local resp
  if [[ -n "$parse_mode" ]]; then
    resp="$(curl -sS -X POST "$send_doc_url" \
      -F "chat_id=${tg_chat_id}" \
      -F "caption=${prefix} ${title}" \
      -F "parse_mode=${parse_mode}" \
      -F "document=@${f}" \
      2>&1)" || {
      echo "WARN: Telegram sendDocument failed: $resp" >&2
      return 1
    }
  else
    resp="$(curl -sS -X POST "$send_doc_url" \
      -F "chat_id=${tg_chat_id}" \
      -F "caption=${prefix} ${title}" \
      -F "document=@${f}" \
      2>&1)" || {
      echo "WARN: Telegram sendDocument failed: $resp" >&2
      return 1
    }
  fi

  if ! grep -q '"ok":true' <<< "$resp"; then
    echo "WARN: Telegram sendDocument response not ok: $resp" >&2
    return 1
  fi
  return 0
}

send_message || true
if [[ -n "$file" ]]; then
  send_document "$file" || true
fi

exit 0
