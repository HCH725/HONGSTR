# Anti-patterns (Research)

**MUST READ FIRST:** `docs/skills/global_red_lines.md`

## Data leakage
- Lookahead features (using future bars)
- Labels not shifted correctly
- Centered rolling windows
- Standardization/normalization fit on full dataset (must fit on train only)

## Evaluation bias
- Survivorship bias (dropping delisted/failed cases)
- Overfitting via repeated tuning on OOS
- Reporting only best runs without full distribution context

## Process violations
- “Research says so -> push to production” shortcuts
- Proposing changes to `src/hongstr/**`
- Committing generated artifacts under `data/**`
- Changing tg_cp to execute or auto-fix (no subprocess/os.system/Popen)
