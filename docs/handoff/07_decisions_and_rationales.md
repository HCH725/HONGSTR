# 🧠 Decisions & Rationales: The Architectural Log

This document records the "Why" behind major design choices to prevent regressions.

---

## 1. Deterministic Out-of-Sample (OOS) Testing

- **Decision**: Force all walk-forward windows to use isolated run directories.
- **Rationale**: Prevent "Data Leakage" where a strategy optimized on 2024 data accidentally sees 2026 price action.
- **Trade-off**: Higher disk usage for `data/backtests/`, but 100% auditability.

## 2. Dynamic Quality Gate Thresholds

- **Decision**: Thresholds (Sharpe, MDD) are not hardcoded but scale based on window length and symbol volatility.
- **Rationale**: A 30-day window and a 365-day window cannot be judged by the same absolute Sharpe.
- **Implementation**: `scripts/calibrate_gate_from_walkforward.py` calculates the "Stability Threshold".

## 3. Pre-Signed URL Execution Pattern

- **Decision**: Avoid passing data into `requests.post(url, data=params)`.
- **Rationale**: Binance (and many other exchanges) are extremely sensitive to whitespace and parameter ordering in HMAC signatures. By signing a query string and appending it to the URL directly, we bypass the internal re-encoding logic of the `requests` library.
- **Safety**: This pattern is verified in `tests/test_binance_utils.py` by checking the `PreparedRequest` body is empty.

## 4. "Action Items" Fault Injection

- **Decision**: Encode common failure patterns into a diagnostic script.
- **Rationale**: Agents often get stuck in "Optimization Loops" without knowing what to change. The `generate_action_items.py` script provides specific code/config suggestions based on failing metrics.

## 5. Hedge Mode (LONG/SHORT) vs One-Way

- **Decision**: Default to `LONG` position side in `BinanceFuturesTestnetBroker`.
- **Rationale**: Most Testnet accounts are created in "Hedge Mode" by default. Attempting a "Both" or "None" side often results in exchange rejections.
- **Future**: If targeting One-Way mode, this logic must be toggled via `os.environ["BINANCE_HEDGE_MODE"]`.
