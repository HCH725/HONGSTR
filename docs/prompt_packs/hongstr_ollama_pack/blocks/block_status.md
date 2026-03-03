# Stable Block: STATUS

A stable markdown block format for status reporting.

Template:
## STATUS
- SSOT_STATUS: <OK|WARN|FAIL|UNKNOWN>
- ts_utc: <iso>
- key_notes: <short>
- next_steps: <short SOP hints>

Rules:
- Must be deterministic and consistent across runs.
- Must not include secrets or local absolute paths.
