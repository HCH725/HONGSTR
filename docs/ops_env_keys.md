# HONGSTR Env Keys (SSOT)

## Canonical keys

- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`
- `OKX_API_KEY`
- `OKX_API_SECRET`
- `OKX_API_PASSPHRASE`
- `OKX_BASE_URL`
- `BITFINEX_API_KEY`
- `BITFINEX_API_SECRET`
- `BITFINEX_BASE_URL`
- `TG_BOT_TOKEN`
- `TG_CHAT_ID`

## Compatibility

- `BINANCE_SECRET_KEY` is accepted and aliased to `BINANCE_API_SECRET` via [`scripts/load_env.sh`](/Users/hong/Projects/HONGSTR/scripts/load_env.sh).
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are accepted and aliased to `TG_BOT_TOKEN` and `TG_CHAT_ID`.
- Current load-env compatibility rules are documented for Binance and Telegram only. OKX and Bitfinex keys above are the intended canonical names for future integrations, but this PR does not add any new runtime aliasing or fetch logic.

## Exchange key usage

### OKX (v5)

- `OKX_API_KEY`: API key for authenticated OKX v5 requests. Optional for public market data; required for private or account data.
- `OKX_API_SECRET`: API secret paired with `OKX_API_KEY` for signed OKX v5 requests. Optional for public market data; required for private or account data.
- `OKX_API_PASSPHRASE`: Passphrase paired with the OKX key set. Optional for public market data; required for private or account data.
- `OKX_BASE_URL`: Base URL for OKX API requests. Keep the default `https://www.okx.com` unless explicitly testing another OKX environment.

### Bitfinex

- `BITFINEX_API_KEY`: API key for authenticated Bitfinex requests. Optional for public market data; required for private or account data.
- `BITFINEX_API_SECRET`: API secret paired with `BITFINEX_API_KEY` for signed Bitfinex requests. Optional for public market data; required for private or account data.
- `BITFINEX_BASE_URL`: Base URL for Bitfinex public API requests. Keep the default `https://api-pub.bitfinex.com` unless an integration explicitly requires another endpoint.

## Policy

- `.env` must remain untracked.
- Never print secrets to logs; sanitize before sending log tails to Telegram.
- Store real exchange keys in local `.env` only. Never commit them, and never include them in logs, Telegram messages, PR text, or screenshots.
