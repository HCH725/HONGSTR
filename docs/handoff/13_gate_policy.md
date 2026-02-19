# Gate Policy

**Last Updated**: 2026-02-18  
**Scope**: `scripts/gate_all.sh` and `reports/gate_latest.md`

## Status Definitions

- `PASS`: step succeeded.
- `WARN`: step degraded but non-blocking.
- `SKIP`: step intentionally not executed due to missing non-critical prerequisite.
- `FAIL`: regression or required step failure.
- `FATAL`: required runtime/tool missing.

## Stop Condition

- Gate stops only on `FAIL` or `FATAL`.
- `WARN` and `SKIP` never stop gate in default mode.

## Exit Code Policy

- Exit `0`: overall `PASS` or `WARN`.
- Exit non-zero: overall `FAIL` or `FATAL`.

## Step Logging Contract

Each step in `reports/gate_latest.md` must include:

- status (`PASS/WARN/SKIP/FAIL/FATAL`)
- command exit code (`rc`)
- step reason (`reason`)

## Why Ruff Is WARN Right Now

`python -m ruff check .` is currently treated as `WARN` on lint violations because the repository has existing lint debt unrelated to Objective 1 runtime correctness.  

`ruff` missing as a module remains `FATAL`.

Supplementary lint signal in gate:

- `python -m ruff check <changed_paths>` is emitted as an additional non-blocking step.
- This step is intended to make touched-file lint debt visible without requiring full-repo cleanup.

## Environment Precheck Contract

`gate_all.sh` must print and persist:

- `python --version`
- `python -m pytest --version` (`NOT_FOUND` if unavailable)
- `python -m ruff --version` (`NOT_FOUND` if unavailable)
- `BINANCE_FUTURES_TESTNET` / `BINANCE_TESTNET` equals `1` or not
- `reports/walkforward_latest.json` presence
- latest `data/backtests/*/*` run_dir detection result

## Walkforward Latest Pointer Policy

- Source of truth for each run is:
  - `reports/walkforward/<RUN_ID>/walkforward.json`
  - `reports/walkforward/<RUN_ID>/walkforward.md`
- `reports/walkforward_latest.json` and `.md` are updated only when:
  - `suite_mode=FULL_SUITE`
  - current run has a new `RUN_ID`
  - `windows_completed == windows_total`
  - no window has `status` in `{FAILED, ERROR}`
- Otherwise, latest pointer is not updated and warning reason must be:
  - `LATEST_NOT_UPDATED_STALE_RISK` or `LATEST_NOT_UPDATED_INCOMPLETE` or `LATEST_NOT_UPDATED_FAILED`
- For quick suites, use explicit token:
  - `LATEST_NOT_UPDATED_QUICK_MODE` (quick is partial by design and never writes latest)
- Rerun flow always uses:
  - `RERUN_NEVER_UPDATES_LATEST_BY_POLICY`
  - `walkforward_rerun_latest.*` (never `walkforward_latest.*`)
- Quick flow may use:
  - `QUICK_SKIPPED_INSUFFICIENT_LOCAL_DATA` when data windows are missing
- Gate/report output must include:
  - per-run directory (`reports/walkforward/<RUN_ID>/`)
  - policy reason enum token (`reason=<TOKEN>`)
  - failed window summary (`failed_windows=<name,...>`)
  - remediation command to rerun suite/report
- When latest is updated successfully, report output must include:
  - `LATEST_UPDATED run_id=<RUN_ID> latest_json=reports/walkforward_latest.json reason=LATEST_UPDATED`
  - gate step reason format: `latest updated -> reports/walkforward_latest.json`

## FULL vs QUICK vs RERUN_SELECTED Semantics

- `run_mode=FULL`: normal walkforward suite/report flow.
- `suite_mode=QUICK`: reduced-window suite for fast local signal; never updates latest pointer.
- `run_mode=RERUN` + `suite_mode=RERUN_SELECTED`: failed-only replay flow from `scripts/rerun_failed_windows.sh`.
- `rerun_scope=FAILED_ONLY`: only windows in `failed_windows_summary` are executed.
- `windows_selected`: replayed windows count.
- `windows_total`: full config windows count.
- `RERUN PARTIAL` (for example `2/5`) is expected and non-fatal.

Rerun artifacts to consume:

- `reports/walkforward_rerun_latest.json`
- `reports/walkforward_rerun_latest.md`

Gate must not treat rerun partial as FAIL/FATAL and must keep `walkforward_latest.*` full-suite-only.

## Exchange Smoke Policy

- Step: `python3 scripts/exchange_smoke_test.py --debug_signing`
- Missing credentials are a deterministic WARN-with-success-exit path:
  - token: `ENV_MISSING_KEYS missing=[BINANCE_API_KEY,BINANCE_API_SECRET]`
  - script exit: `0` (non-blocking)
  - gate class: `WARN` from `SMOKE_RESULT status=WARN reason=ENV_MISSING_KEYS`
- If keys are present but auth/signing/network fails, the script returns non-zero and gate classifies by reason (`AUTH_REJECTED`, `SIGNATURE_MISMATCH`, `NETWORK_ERROR`, etc.).

## Latest pointer update policy

Canonical reason tokens (stable contract):

| token | when it triggers | updates `latest`? | notes |
|---|---|---:|---|
| `LATEST_UPDATED` | full suite completed successfully with no failed windows | yes | overwrites `latest` pointers |
| `LATEST_NOT_UPDATED_QUICK_MODE` | run is **quick mode** (partial windows by design) | no | quick is never allowed to overwrite latest |
| `LATEST_NOT_UPDATED_INCOMPLETE` | run did **not** complete required window set (partial / interrupted) | no | safety: avoid stale-risk overwrite |
| `LATEST_NOT_UPDATED_FAILED` | one or more windows failed | no | safety: failed window blocks overwrite |

Output format requirement (gate + reports):
- Always emit a single-line reason token, e.g. `LATEST_NOT_UPDATED_QUICK_MODE`
- If not updated, include a short `why:` text and any `failed_windows=` / `completed=` diagnostics where available.

