# Stable Block: FRESHNESS (3x3)

Template:
## FRESHNESS
- generated_utc: <iso>
- overall: <OK|WARN|FAIL|UNKNOWN>
- summary:
  - <3 short lines max>
- sop:
  - <2-4 short steps>

Rules:
- Derived only from data/state/freshness_table.json.
- No extra scans; if missing, output UNKNOWN + refresh hint.
