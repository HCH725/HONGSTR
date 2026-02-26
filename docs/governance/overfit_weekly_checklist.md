# Overfit Weekly Checklist (Template)

Use this checklist weekly before any promotion decision. This checklist is report-only and does not auto-modify system state.

## 1) Inputs / Freshness

- [ ] `bash scripts/refresh_state.sh` completed without fatal errors
- [ ] latest `leaderboard` and research artifacts are readable
- [ ] `reports/governance/overfit_weekly_<week_id>.md` generated

## 2) Hard Gates Validation

- [ ] OOS Sharpe floor validated (`>= 0.75`)
- [ ] Max Drawdown ceiling validated (`>= -0.25`)
- [ ] Overfit ratio cap validated (`IS/OOS <= 2.2`)

## 3) Soft Ranking Validation

- [ ] Yield-first soft score calculated with policy weights
- [ ] Top candidates reviewed in descending score order
- [ ] Borderline candidates (`watchlist`) tagged with rationale

## 4) Quant Specialist Output Contract

- [ ] Output has fixed schema fields:
  - `schema_version, week_id, generated_at, report_only, actions, summary, recommendations`
- [ ] `report_only == true`
- [ ] `actions == []`
- [ ] Recommendations only in `{promote, demote, watchlist}`

## 5) PM Signoff

- [ ] Promotion list reviewed by PM
- [ ] Demotion list reviewed by PM
- [ ] Rollback command prepared: `git revert <merge_commit_sha>`

## 6) Audit Pack (copy/paste)

```bash
bash scripts/install_hongstr_skills.sh --force
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
./.venv/bin/python -m pytest -q research/**/tests || true
git diff --name-only origin/main...HEAD | rg '^src/hongstr/' && echo "!! BAD: core changed" && exit 1 || true
rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py && echo "!! BAD: tg_cp exec found" && exit 1 || true
git status --porcelain | rg '^.. data/' && echo "!! BAD: data/** staged" && exit 1 || true
```
