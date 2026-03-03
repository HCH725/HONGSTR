# Skill Spec: execution_quality_report_readonly

## Objective

Provide a read-only report on execution quality (slippage, fill rate, latency) from a canonical SSOT state file.

## SSOT Requirement

This skill requires `data/state/execution_quality_latest.json`.

### Expected Schema (Future)

```json
{
    "generated_utc": "ISO-8601",
    "metrics": {
        "avg_slippage_bps": 1.2,
        "p95_slippage_bps": 5.0,
        "fill_rate": 0.99,
        "avg_latency_ms": 150
    },
    "status": "OK"
}
```

## Current Status (PR-A5)

Stub implementation. Returns `UNKNOWN` because the SSOT file does not yet exist.

- **Message**: "❌ Execution Quality SSOT missing."
- **Guidance**: "Expected file: `data/state/execution_quality_latest.json`. Please ensure the execution audit producer is integrated into `refresh_state.sh`."
