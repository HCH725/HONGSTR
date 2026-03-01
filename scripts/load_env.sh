#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  return 0 2>/dev/null || exit 0
fi

while IFS= read -r raw_line || [[ -n "${raw_line}" ]]; do
  line="${raw_line%$'\r'}"
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"

  [[ -z "${line}" ]] && continue
  [[ "${line}" == \#* ]] && continue
  [[ "${line}" == export\ * ]] && line="${line#export }"

  if [[ "${line}" != *=* ]]; then
    continue
  fi

  key="${line%%=*}"
  val="${line#*=}"
  key="${key#"${key%%[![:space:]]*}"}"
  key="${key%"${key##*[![:space:]]}"}"
  val="${val#"${val%%[![:space:]]*}"}"

  if [[ ! "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    continue
  fi

  if [[ "${val}" == \"*\" && "${val}" == *\" ]]; then
    val="${val:1:${#val}-2}"
  elif [[ "${val}" == \'*\' && "${val}" == *\' ]]; then
    val="${val:1:${#val}-2}"
  fi

  export "${key}=${val}"
done < "${ENV_FILE}"

# Backward compatibility for existing env names.
if [[ -z "${TG_BOT_TOKEN:-}" && -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  export TG_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
fi
if [[ -z "${TG_CHAT_ID:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
  export TG_CHAT_ID="${TELEGRAM_CHAT_ID}"
fi

# Backward/forward compatibility for Binance secret env naming.
# Canonical (recommended): BINANCE_API_KEY + BINANCE_API_SECRET
# Compat: BINANCE_SECRET_KEY (legacy in some modules)
if [[ -z "${BINANCE_API_SECRET:-}" && -n "${BINANCE_SECRET_KEY:-}" ]]; then
  export BINANCE_API_SECRET="${BINANCE_SECRET_KEY}"
fi
if [[ -z "${BINANCE_SECRET_KEY:-}" && -n "${BINANCE_API_SECRET:-}" ]]; then
  export BINANCE_SECRET_KEY="${BINANCE_API_SECRET}"
fi

return 0 2>/dev/null || exit 0
