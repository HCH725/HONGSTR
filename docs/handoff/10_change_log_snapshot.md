# 📸 Change Log Snapshot: Recent Evolutions

Recent major features and refactors implemented in the HONGSTR repository.

---

## 🚀 Feb 2026: The Hardening Phase

### 1. Unified Binance Signing Utility

- **Refactor**: Moved all signing logic to `src/hongstr/execution/binance_utils.py`.
- **Feature**: Implemented `build_signed_request` with deterministic parameter sorting and HMAC signing.
- **Security**: Added deep debug redaction for API Keys and Signatures.

### 2. -1022 Signature Resolution

- **Refactor**: Switched `BinanceFuturesTestnetBroker` to a "URL-Only" request pattern.
- **Impact**: Eliminated the `-1022` error caused by `requests` re-encoding post-sign payloads.

### 3. Regime-Driven Selection

- **Feature**: Added `scripts/generate_selection_artifact.py`.
- **Logic**: Integrates walk-forward window stability into a final `TRADE`/`HOLD` decision.

### 4. Adaptive Quality Gates

- **Feature**: Updated `ExchangeFilters` and `gate_thresholds.json` to handle adaptive Sharpe thresholds.
- **Impact**: More realistic strategy filtering across different market regimes.

---

## 📦 File Modification Summary (Last 48 Hours)

| File Path | Change Type | Purpose |
| :--- | :--- | :--- |
| `src/hongstr/execution/binance_utils.py` | **NEW** | Centralized HMAC signing. |
| `src/hongstr/execution/binance_testnet.py`| **REF** | URL-only POST request implementation. |
| `scripts/execute_paper.py` | **MOD** | Integrated `--debug_signing` and forced qty fixes. |
| `tests/test_binance_utils.py` | **NEW** | Regression suite for signing and empty bodies. |
| `docs/handoff/` | **NEW** | The Codex handoff package. |

---

## 🔜 Next Planned Milestone

- **Live Production Bridge**: Porting the Testnet broker logic to `BinanceFuturesProductionBroker`.
- **Latency Optimization**: Monitoring execution delay in `exchange_smoke_test.py`.
