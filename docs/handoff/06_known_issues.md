# ⚠️ Known Issues: Friction & Troubleshooting

This document tracks known technical limitations, recurring bugs, and the current state of Binance signature troubleshooting.

---

## 🚫 Critical: Binance Futures Testnet -1022 Signature Logic

### Current Status

- **GET /fapi/v2/account**: ✅ Working.
- **POST /fapi/v1/order**: ✅ Working (Hardened).

### Previous Failures & Fixes

Codex **must** be aware that `requests` usually re-encodes parameters when passed via `params=` or `data=`, which corrupts the sign-matched query string.

| Issue | Root Cause | Implementation |
| :--- | :--- | :--- |
| **-1022 (GET)** | Parameter Sorting mismatch | `binance_utils.py` now implements deterministic `sorted(params.items())`. |
| **-1022 (POST)** | Duplicate encoding in Body | `BinanceFuturesTestnetBroker` now uses `params=None, data=None` and sends everything in the URL. |

### How to Reproduce -1022 for Testing

```bash
# Force a trade on Testnet with debug enabled
python3 scripts/execute_paper.py --force_trade --force_side BUY --send --debug_signing
```

**Observation Points**:

1. Check `Prepared Body`: Must be `None`.
2. Check `Pre-Sign QS`: Compare vs `Binance Official API docs`.

---

## 🐢 Environmental & Dependency Issues

### 1. `urllib3` NotOpenSSLWarning

- **Observation**: `NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently ... LibreSSL 2.8.3`.
- **Reason**: macOS default Python/LibreSSL version incompatibility with newer `urllib3`.
- **Impact**: Cosmetic only; does not affect trading performance.
- **Next Step**: Ignore or install Python via `homebrew` with OpenSSL 3.

---

## 🧩 Logical Edge Cases

### 1. Window Status `PENDING`

- **Observation**: Some windows in `walkforward_latest.json` might stay `PENDING`.
- **Reason**: Parallel execution limits or data gap for specific dates.
- **Reproduce**: Run `scripts/walkforward_suite.sh` on very narrow ranges.
- **Next Step**: Ensure `ingest_historical.py` covers all required dates in `configs/windows.json`.

### 2. Rounded Qty 0.0

- **Observation**: Order fails with "Invalid Quantity".
- **Reason**: Calculated quantity (Notional / Price) is smaller than `min_qty` for the pair.
- **Fix**: Increase `--force_notional_usd` (minimum is usually 5.0 - 10.0 USDT).
