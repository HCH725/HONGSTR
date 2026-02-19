# 📊 Artifacts Schema: Data Structures

This document defines the schemas for internal artifacts and external reports used by HONGSTR.

---

## 1. Selection Artifact (`selection.json`)

Produced by `scripts/generate_selection_artifact.py`.

```json
{
  "decision": "TRADE | HOLD",
  "regime": "BULL | BEAR | NEUTRAL | FORCED",
  "selected_symbol": "BTCUSDT",
  "confidence": 0.0 - 1.0,
  "reason": "String description of the logic choice",
  "timestamp": "ISO-8601"
}
```

---

## 2. Walk-Forward Report (`walkforward_latest.json`)

Produced by `scripts/walkforward_suite.sh`.

```json
{
  "generated_at": "ISO-8601",
  "windows_total": 5,
  "windows_completed": 5,
  "windows": [
    {
      "name": "BULL_2024",
      "status": "COMPLETED",
      "gate_overall": "PASS | FAIL",
      "sharpe": 1.5,
      "mdd": -0.05,
      "total_return": 0.12,
      "symbols": ["BTCUSDT", "ETHUSDT"],
      "trades": 500
    }
  ],
  "stability": {
    "BULL": { "mean_sharpe": 1.2, "median_sharpe": 1.1 }
  }
}
```

---

## 3. Order Execution Report (`orders_latest.json`)

Produced by `scripts/execute_paper.py`.

```json
{
  "timestamp": "ISO-8601",
  "decision": "TRADE",
  "forced": true,
  "dry_run": false,
  "orders": [
    {
      "symbol": "BTCUSDT",
      "side": "BUY",
      "status": "FILLED | PARTIALLY_FILLED | REJECTED",
      "executedQty": 0.001,
      "avgPrice": 50000.0,
      "orderId": "123456",
      "clientOrderId": "...",
      "error": "Optional error string"
    }
  ],
  "error": "Global error string (e.g. -1022)"
}
```

---

## 4. Quality Gate Configuration (`gate_thresholds.json`)

Located in `configs/`.

```json
{
  "min_trades_per_day": 0.5,
  "min_sharpe": 0.0,
  "max_mdd": -0.15,
  "adaptive_thresholds": {
    "sharpe_per_symbol": 0.2
  }
}
```

---

## 5. Action Items (`action_items_latest.json`)

Produced by `scripts/generate_action_items.py`.

```json
{
  "overall_gate": "FAIL",
  "top_actions": [
    {
      "rank": 1,
      "title": "Short Description",
      "why": "Observation based on data",
      "changes": ["Specific code/config tweak"],
      "commands": ["Command to run to verify"],
      "verify": ["Target metric (e.g. Sharpe > 0.5)"]
    }
  ]
}
```
