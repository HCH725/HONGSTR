# Rerun Workflow (Failed Windows)

## Goal

Make walkforward failures reproducible without touching core engine or execution code, and keep latest pointer policy safe.

## Policy

- `walkforward_latest.json/.md` are **full-suite only**.
- If run is `FAILED` or `PARTIAL`, latest pointers are **not** overwritten.
- Rerun mode is always `suite_mode=RERUN_SELECTED`, and pointer reason is always
  `RERUN_NEVER_UPDATES_LATEST_BY_POLICY`.
- Rerun outputs are written to:
  - `reports/walkforward_rerun_latest.json`
  - `reports/walkforward_rerun_latest.md`

## Root-Cause Artifacts

For each walkforward run id:

- `reports/walkforward/<RUN_ID>/suite_results.tsv`
- `reports/walkforward/<RUN_ID>/failure_diagnostics.json`
- `reports/walkforward/<RUN_ID>/failure_diagnostics.md`
- `reports/walkforward/<RUN_ID>/walkforward.json`

`failure_diagnostics.*` include:

- `window`
- `reason_code` (example: `INSUFFICIENT_DATA_RESAMPLE`, `NO_DATA_IN_RANGE`)
- `exit_code`
- `log_path`
- `run_out_dir`
- exact `rerun_command`

## One-Click Reproduce

```bash
bash scripts/rerun_failed_windows.sh
```

The script generates:

- rerun run directory under `reports/walkforward/<RERUN_RUN_ID>/`
- rerun summary pointers:
  - `reports/walkforward_rerun_latest.json`
  - `reports/walkforward_rerun_latest.md`

The rerun latest artifact includes:

- `base_failed_windows` (copied from source failed report)
- `rerun_commands` (exact command list used for replay)
- `selected_completed/selected_total/selected_failed`
- `latest_pointers_updated=false`
- `latest_pointer_policy_reason=RERUN_NEVER_UPDATES_LATEST_BY_POLICY`

## Operational Steps

1. Inspect source failure diagnostics:
   - `reports/walkforward/<RUN_ID>/failure_diagnostics.md`
2. Replay only failed windows:
   - `bash scripts/rerun_failed_windows.sh --run_id <RUN_ID>`
3. Rebuild gate summary:
   - `bash scripts/gate_all.sh`
4. If latest is still not updated, check reason in:
   - `reports/gate_latest.md`
   - `reports/walkforward/<RUN_ID>/walkforward.json`
   - `reports/walkforward_rerun_latest.json` (for rerun-only outcomes)
