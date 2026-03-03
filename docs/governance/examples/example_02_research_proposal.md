# Example 2: Research Experiment Proposal (report_only)

## Context

The team wants to evaluate a new BEAR-regime mean-reversion strategy (`bollinger_v3`) to see
if it outperforms the existing `bollinger_revert_v2` on OOS Sharpe.

---

## PRD (Issue: prd label)

**Problem Statement:**
`bollinger_revert_v2` in BEAR regime shows Sharpe ~0.7 and high MDD. We hypothesize that
a tighter band (v3 variant) would reduce MDD without sacrificing Sharpe.

**Non-goals:**

- Not promoting to live trading in this iteration.
- Not modifying any `src/hongstr` execution logic.
- Not changing any gate thresholds.

**Acceptance Criteria:**

```
AC1: research/20260302/bollinger_v3__*/summary.json exists with status=SUCCESS
AC2: All summary.json files contain "report_only": true
AC3: bash scripts/guardrail_check.sh → exits 0
AC4: git diff origin/main...HEAD -- src/hongstr | wc -l → 0
AC5: No subprocess/os.system added to any research script
```

**Risk:** Low — report_only, no execution semantics changed.

**Rollback:** `git revert <merge_commit>` (removes only research outputs from tracking).

---

## Epic (Issue: epic label, refs PRD)

**Scope:**

```
research/<date>/bollinger_v3__*/       # backtest artifacts (report_only)
research/bollinger_v3.py               # new strategy definition
```

**allowed_paths:**

```
allowed_paths:
  - research/bollinger_v3.py
  - research/20260302/bollinger_v3__long__tight_band/
  - research/20260302/bollinger_v3__short__tight_band/
```

**Workstreams:**

```
WS-A: Implement bollinger_v3 strategy class (research/bollinger_v3.py)
WS-B: Run backtest to generate summary.json artifacts
WS-C: Update research leaderboard (data/state/_research/leaderboard.json via state_snapshots.py)
```

**Dependencies:**

- Requires existing `bollinger_revert_v2` baseline in `strategy_pool.json` for comparison.

**Gates:**

```
GATE-1: bash scripts/guardrail_check.sh exits 0
GATE-2: All summary.json files contain "report_only": true
GATE-3: No subprocess in research/ scripts (rg 'subprocess|os\.system' research/ → empty)
GATE-4: OOS Sharpe documented in PR body for human review
```

---

## Task A — Strategy Implementation (Issue: task label, refs Epic)

**allowed_paths:**

```
allowed_paths:
  - research/bollinger_v3.py
```

**Checklist:**

```
- [ ] Implement BollingerV3 class in research/bollinger_v3.py
- [ ] Set report_only = True at module level
- [ ] No subprocess or os.system usage
- [ ] Run bash scripts/guardrail_check.sh
```

**Tests:**

```bash
bash scripts/guardrail_check.sh
rg 'subprocess|os\.system' research/bollinger_v3.py   # must be empty
python3 -c "import research.bollinger_v3; assert research.bollinger_v3.REPORT_ONLY is True"
```

**Rollback:** `git revert <task_a_commit>`

**Flags:** ☐ docs-only  ☑ report_only  ☐ ops

---

## Task B — Backtest Run & Summary (Issue: task label, refs Epic)

**allowed_paths:**

```
allowed_paths:
  - research/20260302/bollinger_v3__long__tight_band/summary.json
  - research/20260302/bollinger_v3__short__tight_band/summary.json
```

**Checklist:**

```
- [ ] Execute backtest (report_only mode)
- [ ] Verify summary.json contains "status": "SUCCESS" and "report_only": true
- [ ] Run bash scripts/guardrail_check.sh
- [ ] Do not commit data/** artifacts
```

**Tests:**

```bash
bash scripts/guardrail_check.sh
git ls-files | rg '\.(parquet|pkl)$'   # must be empty
python3 -c "import json; d=json.load(open('research/20260302/bollinger_v3__long__tight_band/summary.json')); assert d['report_only'] is True"
```

**Rollback:** `git revert <task_b_commit>`

**Flags:** ☐ docs-only  ☑ report_only  ☐ ops
