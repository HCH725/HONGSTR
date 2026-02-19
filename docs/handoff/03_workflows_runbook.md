# 🏃 Runbook: Core Workflows & SOPs

Standard Operating Procedures for running, testing, and debugging the HONGSTR system.

---

## 🛠️ Data & Environment Preparation

### 1. Initialize Environment

```bash
# Setup virtualenv and paths
source .venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

### 2. Check Connectivity (Binance Testnet)

```bash
python3 scripts/exchange_smoke_test.py --debug_signing
```

---

## 📈 Backtesting & Optimization

### 3. Run a Basic Backtest

```bash
python3 scripts/run_backtest.py --symbol BTCUSDT --strategy vwap_supertrend
```

### 4. Run Full Walkforward Suite

```bash
# Runs all windows defined in configs/windows.json
bash scripts/walkforward_suite.sh
```

### 5. Quick Verification (Reduced dataset)

```bash
# Runs walkforward with 10% data for fast checks
bash scripts/walkforward_suite.sh --quick
```

### 5.1 Rerun FAILED windows only (and refresh walkforward report)

```bash
# Preview commands without running backtests
bash scripts/rerun_failed_windows.sh --report_json reports/walkforward/<RUN_ID>/walkforward.json --dry-run

# Execute rerun for failed windows and regenerate reports/walkforward/<NEW_RUN_ID>/walkforward.json
bash scripts/rerun_failed_windows.sh --report_json reports/walkforward/<RUN_ID>/walkforward.json
```

Rerun semantics:

- `run_mode=RERUN`, `rerun_scope=FAILED_ONLY`.
- `windows_selected` is the number of replayed failed windows.
- `windows_total` remains full config windows count.
- `PARTIAL (selected/total)` is expected for failed-only replay.

Rerun writes consumer artifacts:

- `reports/walkforward_rerun_latest.json`
- `reports/walkforward_rerun_latest.md`

Full-suite latest pointer policy remains separate. `walkforward_latest.*` is only updated by full-suite success:

- `reports/walkforward_latest.json`
- `reports/walkforward_latest.md`
 
Rerun never overwrites `walkforward_latest.*`.

---

## ⚖️ Decision & Execution

### 6. Generate Decision (Selection)

```bash
# Calibrates gate and determines TRADE/HOLD
python3 scripts/generate_selection_artifact.py
```

### 7. Execute Order (Dry-Run)

```bash
# Safe default logic
python3 scripts/execute_paper.py
```

### 8. Execute Order (Live Force BUY on Testnet)

```bash
# 🛑 WARNING: This sends a real order to Testnet
python3 scripts/execute_paper.py --force_trade --force_side BUY --send --debug_signing
```

---

## 🔍 Debugging & Maintenance

### 9. Analyze Failures

```bash
# Generate actionable fixes for poor sharpe/returns
python3 scripts/generate_action_items.py
```

### 10. Reconcile Recent Orders

```bash
# Verify order status on exchanges
python3 scripts/order_reconcile.py
```

---

## 🚨 Troubleshooting SOP

### Binance -1022 (Signature Failure)

1. Run with `--debug_signing`.
2. Check `Prepared Body`: Must be `None`.
3. Check `Prepared URL`: Ensure `signature=` is at the end.
4. Check `Timestamp Drift`: Use `exchange_smoke_test.py` to check local vs server time.

### Filter/Quantity Error

1. Check `reports/orders_latest.json`.
2. If `error` mentions `min_qty`, increase `--force_notional_usd`.
