# 🥾 Codex Bootstrap: Your First 60 Minutes

Welcome, Codex. This guide provides the exact steps to verify HONGSTR and begin contributing without breaking the "Golden Path".

---

## 📅 Day 0 Checklist

### 0. Bootstrap Dev Environment (Min 3)

```bash
bash scripts/bootstrap_dev_env.sh
```

**Success Criteria**:

- `.venv` exists
- `pip install -e ".[dev]"` completes

### 1. Environment Verification (Min 5)

```bash
# Verify imports and basic logic
./.venv/bin/python -m pytest -q tests/test_binance_utils.py tests/test_execute_paper.py
```

### 2. Connectivity Baseline (Min 10)

```bash
# Check Testnet status and Redaction logic
./.venv/bin/python scripts/exchange_smoke_test.py --debug_signing
```

**Success Criteria**:

- `Testnet: True`
- `BINANCE_API_KEY present: True/False` and `BINANCE_API_SECRET present: True/False`
- if keys are missing, script prints `[SKIP] missing BINANCE_API_KEY/SECRET -> skipping private account check`

### 3. Engine Baseline (Min 15)

```bash
# Run a quick walkforward to verify engine determinism
bash scripts/walkforward_suite.sh --quick
```

**Success Criteria**:

- New run artifact exists at `reports/walkforward/<RUN_ID>/walkforward.json`
- only complete runs update `reports/walkforward_latest.json`

### 4. Decision Logic Verification (Min 20)

```bash
# Generate a fresh selection artifact
./.venv/bin/python scripts/generate_selection_artifact.py --run_dir <latest_run_dir>
```

**Success Criteria**:

- `selection.json` exists and matches `reports/walkforward_latest.json` decisions.

---

## 🛑 Prohibited Actions (Read Carefully)

1. **Do Not** modify `src/hongstr/backtest/engine.py` without a failing test case that demonstrates a bug in "Next-Open" logic.
2. **Do Not** pass parameters into the `data=` argument of `requests` for Binance endpoints. Use the "URL-Only" pattern in `BinanceFuturesTestnetBroker`.
3. **Do Not** commit files to `data/backtests/`. Keep the repository clean of large parquet files.

---

## 🎯 Your First Task Suggestion

If the system is healthy, look at `reports/action_items_latest.md`.  
Follow the suggested commands there to improve the the Sharpe ratio of the `BEAR_2022` window.

---

## 🔗 Reference Path

- [00_index.md](file:///Users/hong/Projects/HONGSTR/docs/handoff/00_index.md) (All Docs)
- [03_workflows_runbook.md](file:///Users/hong/Projects/HONGSTR/docs/handoff/03_workflows_runbook.md) (All Commands)
