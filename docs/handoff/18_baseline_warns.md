
# Baseline WARN/SKIP Playbook

## Known non-blocking statuses

### 1) `ENV_MISSING_KEYS` (exchange_smoke_test)
- Expected when `BINANCE_API_KEY/BINANCE_API_SECRET` not set.
- This step is classified as WARN (external/network) by policy.

### 2) `LATEST_NOT_UPDATED_STALE_RISK`
- When walkforward has failed windows, policy blocks overwriting `walkforward_latest.*`
- Use rerun artifacts (`walkforward_rerun_latest.*`) or run full suite to update.

### 3) `walkforward_suite --quick` SKIP: insufficient local data
- Expected when local dataset does not cover configured windows.
- Remedy: fetch/build required local data for the configured window ranges, then rerun.
