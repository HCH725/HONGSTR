> [!IMPORTANT] REFERENCE ONLY - Please see [Daily Report & Glossary](docs/ops/daily_report_zh.md) for current entry point.

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

## Safety

- report-only only
- no `src/hongstr/**` changes
- no `data/**` committed

## Verification

```bash
./.venv/bin/python -m pytest -q research/loop/tests/test_candidate_catalog.py
./.venv/bin/python -m pytest -q research/loop/tests/test_leaderboard_direction.py
```
