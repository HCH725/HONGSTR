#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
source "${REPO_ROOT}/scripts/load_env.sh"

title=""
body=""
status="ok"
link=""
file=""
log_tail=""
tail_lines="60"
parse_mode="${TG_PARSE_MODE:-Markdown}"
tg_disable="${TG_DISABLE:-0}"
tg_timeout="${TG_TIMEOUT:-8}"
tg_retries="${TG_RETRIES:-3}"
tg_backoff="${TG_RETRY_BACKOFF_SEC:-2}"
tg_connect_timeout="${TG_CONNECT_TIMEOUT:-5}"

redact_string() {
  local s="$1"
  s="$(echo "$s" | sed -E 's/(api\.telegram\.org\/bot)[^\/]+/\1***REDACTED***/g')"
  s="$(echo "$s" | sed -E 's/((^|[^A-Z0-9_])(KEY|SECRET|TOKEN)[A-Z0-9_]*[[:space:]]*[:=][[:space:]]*)[^ ,;"]+/\1***REDACTED***/gI')"
  s="$(echo "$s" | sed -E 's/(BINANCE_API_KEY[[:space:]]*=[[:space:]]*)[^ ,;"]+/\1***REDACTED***/gI')"
  s="$(echo "$s" | sed -E 's/(BINANCE_API_SECRET[[:space:]]*=[[:space:]]*)[^ ,;"]+/\1***REDACTED***/gI')"
  s="$(echo "$s" | sed -E 's/(BINANCE_SECRET_KEY[[:space:]]*=[[:space:]]*)[^ ,;"]+/\1***REDACTED***/gI')"
  echo "$s"
}

redact_file_inplace() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  sed -i '' -E 's/(api\.telegram\.org\/bot)[^\/]+/\1***REDACTED***/g' "$f" 2>/dev/null || true
  sed -i '' -E 's/((^|[^A-Z0-9_])(KEY|SECRET|TOKEN)[A-Z0-9_]*[[:space:]]*[:=][[:space:]]*)[^ ,;"]+/\1***REDACTED***/gI' "$f" 2>/dev/null || true
  sed -i '' -E 's/(BINANCE_API_KEY[[:space:]]*=[[:space:]]*)[^ ,;"]+/\1***REDACTED***/gI' "$f" 2>/dev/null || true
  sed -i '' -E 's/(BINANCE_API_SECRET[[:space:]]*=[[:space:]]*)[^ ,;"]+/\1***REDACTED***/gI' "$f" 2>/dev/null || true
  sed -i '' -E 's/(BINANCE_SECRET_KEY[[:space:]]*=[[:space:]]*)[^ ,;"]+/\1***REDACTED***/gI' "$f" 2>/dev/null || true
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) title="${2:-}"; shift 2 ;;
    --body) body="${2:-}"; shift 2 ;;
    --status) status="${2:-ok}"; shift 2 ;;
    --link) link="${2:-}"; shift 2 ;;
    --file) file="${2:-}"; shift 2 ;;
    --log-tail) log_tail="${2:-}"; shift 2 ;;
    --tail-lines) tail_lines="${2:-60}"; shift 2 ;;
    *)
      if [[ -z "$body" ]]; then
        body="$1"
      else
        body="${body}\n$1"
      fi
      shift
      ;;
  esac
done

if [[ -n "$log_tail" && -f "$log_tail" ]]; then
  tail_file="/tmp/hongstr_tg_tail_$(date +%Y%m%d_%H%M%S).log"
  trap 'rm -f "$tail_file" 2>/dev/null || true' EXIT
  if [[ "$tail_lines" =~ ^[0-9]+$ ]]; then
    tail -n "$tail_lines" "$log_tail" > "$tail_file" 2>/dev/null || true
  else
    tail -n 60 "$log_tail" > "$tail_file" 2>/dev/null || true
  fi
  if [[ -s "$tail_file" ]]; then
    redact_file_inplace "$tail_file"
    file="$tail_file"
  fi
fi

tg_token="${TG_BOT_TOKEN:-}"
tg_chat_id="${TG_CHAT_ID:-}"
if [[ "$tg_disable" == "1" ]]; then
  echo "WARN: Telegram disabled by TG_DISABLE=1; skip notify." >&2
  exit 0
fi
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

if ! [[ "$tg_retries" =~ ^[0-9]+$ ]] || [[ "$tg_retries" -lt 1 ]]; then
  tg_retries=3
fi
if ! [[ "$tg_backoff" =~ ^[0-9]+$ ]] || [[ "$tg_backoff" -lt 1 ]]; then
  tg_backoff=2
fi
if ! [[ "$tg_connect_timeout" =~ ^[0-9]+$ ]] || [[ "$tg_connect_timeout" -lt 1 ]]; then
  tg_connect_timeout=5
fi

extract_http_code() {
  local payload="$1"
  echo "$payload" | sed -n 's/.*__HTTP_CODE__:\([0-9][0-9][0-9]\).*/\1/p' | tail -n 1
}

extract_body() {
  local payload="$1"
  echo "$payload" | sed '/__HTTP_CODE__:[0-9][0-9][0-9]/d'
}

extract_desc() {
  local body="$1"
  local desc
  desc="$(echo "$body" | sed -n 's/.*"description":"\([^"]*\)".*/\1/p' | head -n 1)"
  if [[ -z "$desc" ]]; then
    desc="$(echo "$body" | tr '\n' ' ' | cut -c1-160)"
  fi
  echo "$desc"
}

retry_send() {
  local action="$1"
  shift
  local attempt=1
  local max_attempts="$tg_retries"
  local last_reason="unknown"

  while [[ "$attempt" -le "$max_attempts" ]]; do
    local err_file="/tmp/hongstr_tg_err_${action}_${attempt}_$$.log"
    local payload=""
    set +e
    payload="$(curl -sS --connect-timeout "$tg_connect_timeout" --max-time "$tg_timeout" -w $'\n__HTTP_CODE__:%{http_code}' "$@" 2>"$err_file")"
    local curl_rc=$?
    set -e
    local err_text=""
    [[ -f "$err_file" ]] && err_text="$(cat "$err_file")"
    rm -f "$err_file" || true

    local retryable=0
    if [[ "$curl_rc" -eq 0 ]]; then
      local body
      body="$(extract_body "$payload")"
      local http_code
      http_code="$(extract_http_code "$payload")"
      if grep -q '"ok":true' <<< "$body"; then
        echo "INFO: Telegram ${action} ok"
        return 0
      fi

      local desc
      desc="$(extract_desc "$body")"
      if [[ "$http_code" =~ ^5 ]]; then
        last_reason="api_5xx(${http_code}): ${desc}"
        retryable=1
      elif [[ "$http_code" =~ ^4 ]]; then
        last_reason="api_4xx(${http_code}): ${desc}"
        retryable=0
      else
        last_reason="api_error(${http_code:-unknown}): ${desc}"
        retryable=1
      fi
    else
      if grep -qi "Could not resolve host" <<< "$err_text"; then
        last_reason="dns: Could not resolve host"
        retryable=1
      elif [[ "$curl_rc" -eq 28 ]] || grep -Eqi "Operation timed out|timed out" <<< "$err_text"; then
        last_reason="timeout"
        retryable=1
      else
        last_reason="curl_exit_${curl_rc}: $(redact_string "$err_text" | tr '\n' ' ' | cut -c1-140)"
        retryable=1
      fi
    fi

    if [[ "$retryable" -eq 1 && "$attempt" -lt "$max_attempts" ]]; then
      local sleep_sec=$((tg_backoff * (2 ** (attempt - 1))))
      echo "WARN: Telegram ${action} attempt ${attempt}/${max_attempts} failed (${last_reason}); retry in ${sleep_sec}s" >&2
      sleep "$sleep_sec"
      attempt=$((attempt + 1))
      continue
    fi

    break
  done

  echo "WARN: Telegram ${action} failed after ${attempt} attempts: ${last_reason}" >&2
  return 1
}

send_message() {
  if [[ -n "$parse_mode" ]]; then
    retry_send "sendMessage" -X POST "$send_msg_url" \
      --data-urlencode "chat_id=${tg_chat_id}" \
      --data-urlencode "text=${msg}" \
      --data-urlencode "parse_mode=${parse_mode}"
  else
    retry_send "sendMessage" -X POST "$send_msg_url" \
      --data-urlencode "chat_id=${tg_chat_id}" \
      --data-urlencode "text=${msg}"
  fi
}

send_document() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  if [[ -n "$parse_mode" ]]; then
    retry_send "sendDocument" -X POST "$send_doc_url" \
      -F "chat_id=${tg_chat_id}" \
      -F "caption=${prefix} ${title}" \
      -F "parse_mode=${parse_mode}" \
      -F "document=@${f}"
  else
    retry_send "sendDocument" -X POST "$send_doc_url" \
      -F "chat_id=${tg_chat_id}" \
      -F "caption=${prefix} ${title}" \
      -F "document=@${f}"
  fi
}

send_message || true
if [[ -n "$file" ]]; then
  send_document "$file" || true
fi

exit 0
