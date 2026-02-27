# Direction Variants Reporting (LONG / SHORT / LONGSHORT + Regime Slice B1)

> REFERENCE ONLY


Research loop now evaluates direction variants from candidate catalog and keeps direction metadata through all report-only artifacts.
Regime Timeline SSOT (B1) adds an optional regime slice label (`ALL|BULL|BEAR|SIDEWAYS`) without changing default behavior.

## Source of Truth

- Catalog: `research/policy/candidate_catalog.json`
- Builder: `research/loop/candidate_catalog.py`

## Artifact Fields

Direction and variant must appear in:

- `summary.json`
- `gate.json`
- `selection.json`
- `data/state/_research/leaderboard.json`

Regime B1 metadata appears in the same artifacts:

- `regime` / `regime_slice`
- `regime_window_start_utc`
- `regime_window_end_utc` (end-exclusive `[start,end)`)
- `regime_window_utc` (canonical text form `[start,end)`)
- `slice_rationale` / `fallback_reason`
- `slice_comparison_key` (`strategy_id|direction|variant|regime_slice`) for cross-slice comparability

## Safety

- report-only only
- no `src/hongstr/**` changes
- no `data/**` committed

## Verification

```bash
./.venv/bin/python -m pytest -q research/loop/tests/test_candidate_catalog.py
./.venv/bin/python -m pytest -q research/loop/tests/test_leaderboard_direction.py
```

## How To Run (B1 Wiring)

```bash
# Default (unchanged)
./.venv/bin/python research/loop/research_loop.py --dry-run

# Optional regime slice (B1 wiring only)
HONGSTR_REGIME_SLICE=BULL ./.venv/bin/python research/loop/research_loop.py --dry-run
# or
./.venv/bin/python research/loop/research_loop.py --dry-run --regime BULL
```

> B1 scope: wiring/metadata only. B2 will handle regime-aware leaderboard weighting/aggregation.
