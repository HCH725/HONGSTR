# Direction Variants Reporting (LONG / SHORT / LONGSHORT)

Research loop now evaluates direction variants from candidate catalog and keeps direction metadata through all report-only artifacts.

## Source of Truth

- Catalog: `research/policy/candidate_catalog.json`
- Builder: `research/loop/candidate_catalog.py`

## Artifact Fields

Direction and variant must appear in:

- `summary.json`
- `gate.json`
- `selection.json`
- `data/state/_research/leaderboard.json`
- `reports/research/governance/*/weekly_quant_checklist.{json,md}`

## SHORT Coverage (Required in Reporting)

Both leaderboard and weekly governance outputs must expose:

- `candidate_count` (direction=`SHORT`)
- `gate_passed_count` (`gate_overall=PASS` within SHORT candidates)
- `best_entry` (top SHORT row by score)

## Safety

- report-only only
- no `src/hongstr/**` changes
- no `data/**` committed

## Verification

```bash
./.venv/bin/python -m pytest -q research/loop/tests/test_candidate_catalog.py
./.venv/bin/python -m pytest -q research/loop/tests/test_leaderboard_direction.py
```
