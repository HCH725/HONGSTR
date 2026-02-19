# 🔒 Security & Operations: Guardrails

Safe operation of HONGSTR requires strict adherence to secret management and execution modes.

---

## 🔑 Secret Management

HONGSTR follows a "Zero Leak" policy for API keys and secrets.

### 1. Environment Variables

Secrets **MUST NEVER** be hardcoded. Use the `.env` file (which is gitignored).

- `BINANCE_API_KEY`: Restricted key (Testnet or Live).
- `BINANCE_API_SECRET`: **Extremely sensitive**.
- `TELEGRAM_TOKEN`: For alerts.

### 2. Logging & Redaction

The `src/hongstr/execution/binance_utils.py` module automatically redacts sensitive info:

- **API Key**: Truncated to `prefix... (len)`.
- **API Secret**: Completely scrubbed from logs.
- **Signature**: Redacted to `prefix... ****`.

---

## 🛠️ Execution Modes & Safety

### 1. Testnet Safeguard

The `BinanceFuturesTestnetBroker` will **only** talk to Testnet domains.

- **Check**: Run `python3 scripts/exchange_smoke_test.py` and confirm `Testnet: True`.

### 2. Dry-Run Default

`scripts/execute_paper.py` will NEVER send an order unless the `--send` flag is explicitly passed.

- **Codex Rule**: Always perform a Dry-Run first and inspect `reports/orders_latest.json`.

### 3. Isolated Margin Enforcement

The system automatically checks symbols for `ISOLATED` margin before trading. If a symbol is in `Cross` margin, execution will fail with a `CRIT` alert to prevent unintended account-wide liquidation risk.

---

## 📡 Operational Monitoring

- **Logs**: Located in `logs/` (if configured) or redirected from stdout.
- **Alerts**: Sent via Telegram if `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are set.
- **Reconcile**: Run `scripts/order_reconcile.py` every hour to ensure the local state matches the exchange.
