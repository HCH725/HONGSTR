---
date: YYYY-MM-DD
ssot_ts_utc: ""
linked_pr: "#NNN"
linked_issue: "#NNN"
status: draft   # draft | complete | abandoned
experiment_id: ""      # matches reports/ directory (e.g. trend_mvp_btc_1h)
dataset_hash: ""       # sha256 of input parquet manifest or klines range
---

# Research Experiment: {{ experiment_id }}

## Hypothesis
<!-- One sentence: what are you testing and why? -->

## Dataset

| Field | Value |
|-------|-------|
| Symbols | |
| Timeframe | |
| IS period | YYYY-MM-DD → YYYY-MM-DD |
| OOS period | YYYY-MM-DD → YYYY-MM-DD |
| WF windows | N |
| Dataset hash | `{{ dataset_hash }}` |
| SSOT ts_utc | `{{ ssot_ts_utc }}` |

## Gate Results

| Gate | Threshold | Result | Pass? |
|------|-----------|--------|-------|
| OOS Sharpe ≥ | | | ✅/❌ |
| Max DD ≤ | | | ✅/❌ |
| IS Sharpe ≥ | | | ✅/❌ |
| Trade count ≥ | | | ✅/❌ |

## Key Metrics

| Metric | IS | OOS | Delta |
|--------|----|-----|-------|
| Sharpe | | | |
| CAGR | | | |
| Max DD | | | |
| Win Rate | | | |

## Conclusion
<!-- Definitive, verifiable conclusion. Avoid hedging. -->
- **Promoted?** yes / no
- **Reason:**

## Next Steps

1.
2.

## Artefact Paths

- Report: `reports/research/{{ date }}/{{ experiment_id }}/summary.json`
- Backtest bundle: (if worker_inbox)

## References

- Linked PR: {{ linked_pr }}
- Linked Issue: {{ linked_issue }}
