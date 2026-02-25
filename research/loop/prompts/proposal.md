### Research Proposal Template

Based on the provided system snapshot, please generate a research proposal in JSON format.
Your proposal must address observed anomalies or potential for optimization.

**Snapshot Context**:
{{snapshot_json}}

**Registry Constraints**:
{{registry_json}}

**Required JSON Format**:

```json
{
  "experiment_id": "EXP_YYYYMMDD_HHMM",
  "priority": "HIGH|MED|LOW",
  "hypothesis": "...",
  "strategy": "...",
  "symbol": "...",
  "timeframe": "...",
  "parameters": {
    "key": value
  },
  "metrics_to_watch": ["..."],
  "reasoning": "Detailed explanation linking snapshot data to this experiment."
}
```

**Self-Correction Checklist**:

- Is the strategy in the `allowed_strategies`?
- Are parameters within `parameter_ranges`?
- Is there ANY forbidden keyword? (Fail if yes)
- Does the reasoning cite specific snapshot metrics?
