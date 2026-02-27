# PM Snapshot Runbook

Guide for running the `scripts/pm_snapshot.sh` utility and interpreting its output.

## Execution

```bash
bash scripts/pm_snapshot.sh
```

The script is safe, idempotent, and performs a full refresh of the system state before reporting.

## Interpreting Failures

If the script fails, identify the error source below:

### 1. "Forbidden core diff detected"

- **Cause**: You have local changes in `src/hongstr/` which is protected.
- **Action**: Stash your changes or revert them. Core engine changes require a separate, highly-vetted PR.

### 2. "Forbidden exec calls detected in tg_cp_server.py"

- **Cause**: The Telegram Control Plane is `no-exec`. You cannot add subprocess calls.
- **Action**: Remove any `os.system`, `subprocess`, or `Popen` calls from the tg_cp code.

### 3. "Forbidden data/ artifacts staged"

- **Cause**: Binary/Data files (`.parquet`, `.json`, `.pkl`) are staged for git.
- **Action**: Run `git reset data/` followed by updating `.gitignore` if necessary. Never commit data files.

### 4. "HealthPack not found"

- **Cause**: The state refresh failed or the SSOT boundary was violated.
- **Action**: Run `bash scripts/refresh_state.sh` manually and check for errors in the logs.

---
Safety Level: High (Read-only / Audit)
