# HONGSTR Env Keys (SSOT)

## Canonical keys

- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`
- `TG_BOT_TOKEN`
- `TG_CHAT_ID`

## Compatibility

- `BINANCE_SECRET_KEY` is accepted and aliased to `BINANCE_API_SECRET` via [`scripts/load_env.sh`](/Users/hong/Projects/HONGSTR/scripts/load_env.sh).
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are accepted and aliased to `TG_BOT_TOKEN` and `TG_CHAT_ID`.

## Policy

- `.env` must remain untracked.
- Never print secrets to logs; sanitize before sending log tails to Telegram.
