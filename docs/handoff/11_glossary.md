# 📖 Glossary: Terminology & Core Concepts

Commonly used terms in the HONGSTR ecosystem.

---

## 🏗️ System Logic

### Regime

A classification of market conditions (e.g., **BULL**, **BEAR**, **NEUTRAL**). Strategies are often evaluated based on their performance "Switching" between these.

### Quality Gate

A filter layer that determines if a strategy is fit for execution. It tests against thresholds like `min_sharpe` and `max_mdd`.

### Selection

The final binary decision logic. It combines regime analysis and quality gate output to decide whether to **TRADE** or **HOLD** a specific symbol.

---

## 🧪 Backtesting Terms

### Walk-Forward (WF)

The process of running a strategy through successive "Out-of-Sample" (OOS) windows to verify that it wasn't just overfit to a specific period.

### Determinism

The property where the same code and same data always produce the 100% identical PnL and trades.

### Lookahead Bias

The common error of using future data to make a past trading decision (e.g., using 'Close' price of today to buy at 'Open' price of today).

---

## 💸 Trading & Risk

### Notional USD

The total dollar value of a position (Quantity * Price). HONGSTR uses `--max_notional_usd` to prevent oversized trades.

### Exposure

The total amount of capital currently at risk in open positions.

### Sharpe Ratio

A measure of risk-adjusted return. HONGSTR targets `Sharpe > 1.0` for valid TRADE decisions.

### Drawdown (MDD)

The peak-to-trough decline during a specific period. Gating typically sets a `max_mdd` of `-15%`.

### HMAC Signing

The authentication method for Binance. Requires a sorted query string and a secret key to produce a hex signature.
