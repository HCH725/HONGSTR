# 🧪 Test Matrix: Verification & Coverage

HONGSTR relies on a multi-layer testing strategy to ensure determinism and execution safety.

---

## 🏗️ Test Layers

### 1. Unit Tests (`tests/`)

Targeted at individual functions and logic.

| Suite | Focus | Command |
| :--- | :--- | :--- |
| `test_binance_utils.py` | Deterministic Signing | `pytest tests/test_binance_utils.py` |
| `test_gate_artifact.py` | Quality Gate Thresholds | `pytest tests/test_gate_artifact.py` |
| `test_execute_paper.py` | Dry-Run Logic | `pytest tests/test_execute_paper.py` |
| `test_backtest_engine.py`| Fill Accuracy | `pytest tests/test_backtest_engine.py` |

### 2. Smoke Tests (`scripts/`)

End-to-end verifications of integrated workflows.

| Task | Script | Expected Result |
| :--- | :--- | :--- |
| Connectivity | `exchange_smoke_test.py` | Server time sync; balance fetched. |
| Engine Integration | `smoke_backtest.sh` | Successful run across 1 window. |
| Selection Logic | `generate_selection_artifact.py` | Valid `selection.json` produced. |

### 3. Integrated Walk-Forward (`scripts/`)

Validates stability and prevents overfitting.

| Mode | Command | Duration |
| :--- | :--- | :--- |
| Full Suite | `bash scripts/walkforward_suite.sh` | ~10-15 mins |
| Quick Check | `bash scripts/walkforward_suite.sh --quick` | ~2 mins |

---

## 🛡️ Critical Verification Steps (Post-Merge Checklist)

Before any PR is merged to "Safe/Live", Codex **must** verify:

1. **Determinism**: Run the same backtest twice; binary diff `equity_curve.parquet`.
2. **Safety**: Run `execute_paper.py` (dry-run) and confirm `orders_latest.json` status is `DRY_RUN`.
3. **Signatures**: Run `exchange_smoke_test.py --debug_signing` and verify `Prepared Body: None`.
4. **Lints**: Run `ruff check .` to ensure code quality hasn't regressed.

---

## 📈 Coverage Summary (Targets)

- **Core Logic (`src/hongstr/backtest`)**: > 90%
- **Execution Transport (`src/hongstr/execution`)**: > 80% (Mocked)
- **Regime/Selection**: > 70%
