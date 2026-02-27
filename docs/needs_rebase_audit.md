# HONGSTR NEEDS_REBASE Audit (R5-C)

> REFERENCE ONLY


## 1) Objective

Verify whether NEEDS_REBASE is an explicit system signal, and document its producer/consumer chain.

## 2) Definitions

- **NEEDS_REBASE**: A signal indicating that a previously completed backtest or coverage row is now invalid due to a change in the underlying data/fee/matching semantics.
- **Producer**: `scripts/semantics_check.py`.
- **Consumer**: Web Dashboard (via `coverage_latest.json`), `web/app/api/status/route.ts`.

## 3) Evidence search

- **Keywords**: `NEEDS_REBASE`, `coverage_table.jsonl`, `semantics_version.json`.
- **Paths searched**: `scripts/`, `research/`, `docs/`, `_local/`, `web/`.
- **Commands used**: `rg -ni "NEEDS_REBASE"`, `view_file scripts/semantics_check.py`.

## 4) Findings (FOUND)

### Existence

- **Is NEEDS_REBASE present as a literal/status anywhere?**
- **Status**: **FOUND**. It exists as a string value for the `status` field in `data/state/coverage_table.jsonl`.

### Producer

- **File(s)/job(s)**: `scripts/semantics_check.py`.
- **Trigger condition**: When the `version` field in `configs/semantics_version.json` mismatches the `semantics_version` stored inside a `coverage_table.jsonl` row's `coverage_key`.
- **Output artifact path**: `data/state/coverage_table.jsonl` (modified in-place).

### Consumer

- **tg_cp command(s)**: **MISSING**. Current `/status` implementation only reads `freshness_table.json`, which does not yet include semantic status.
- **dashboard component(s)**: **FOUND**. The dashboard API (`route.ts`) parses the coverage summaries and increments a `rebase` counter.
- **report(s)**: `data/state/coverage_summary.json` (produced by `state_snapshots.py`) counts these as non-PASS, effectively lowering the global system readiness score.

## 5) Nearest equivalents (if NOT FOUND)

- `freshness_table` FAIL: Indicates data is too old (time drift).
- `regime_monitor` WARN: Indicates performance drift (anomaly).
- `NEEDS_REBASE` specifically targets **semantic drift** (code/logic change).

## 6) Recommendation (next minimal PR)

- **Surfacing**: Update `_local/telegram_cp/tg_cp_server.py` to include a one-line "Semantic Status" in `/status` by reading `data/state/coverage_summary.json`.
- **Example**: `• Semantics: ⚠️ 80% DONE (2 NEEDS_REBASE)`
- **Safety**: This remains strictly read-only and follows the existing snapshot architecture.
