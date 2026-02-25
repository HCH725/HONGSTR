# Guardrails Dedupe Plan (Single-SSOT Policy)

Last updated (UTC): 2026-02-25T15:39:15Z

## 1) Current Guardrail Sources (and overlap)

| Layer | Source | Evidence | Current role | Overlap / issue |
|---|---|---|---|---|
| Policy SSOT | `docs/skills/global_red_lines.md` | `docs/skills/global_red_lines.md:1-23` | Canonical non-negotiables for all agents. | Correct source; should be referenced, not re-written repeatedly. |
| PR authoring | `.github/pull_request_template.md` | `.github/pull_request_template.md:13-19` | Requires safety statement in PR body. | Duplicates wording with docs; no machine enforcement. |
| Local guardrail script | `scripts/guardrail_check.sh` | `scripts/guardrail_check.sh:23-31` | Blocks core-path changes and artifact commits. | Does not enforce tg_cp no-exec regex, report_only stance, or Telegram-only policy. |
| CI/ops gate | `scripts/gate_all.sh` | `scripts/gate_all.sh:255-276` | Detects protected path touches during gate run. | Protection scope is narrower (`backtest/`, `execution/`) than full `src/hongstr/**`. |
| tg_cp runtime guard | `_local/telegram_cp/guardrail.py` + server pre/post check | `_local/telegram_cp/guardrail.py:33-49`, `_local/telegram_cp/tg_cp_server.py:1834-1843`, `:1905-1908` | Runtime refusal of action/execution intents in Telegram plane. | Strong runtime fence, but separate from git/CI checks. |
| Planning docs | `docs/slimdown_inventory.md`, `docs/slimdown_plan.md` | `docs/slimdown_inventory.md:3-9`, `docs/slimdown_plan.md:90-93` | Process guidance and checklist. | Repeated rule text causes drift risk across documents. |

## 2) Single-SSOT Guardrail Model

### Canonical source of truth
- Keep **one policy source**: `docs/skills/global_red_lines.md`.

### Enforcement mapping
- **Authoring-time reminder**: `.github/pull_request_template.md`
- **Local preflight hard checks**: `scripts/guardrail_check.sh`
- **CI/merge hard checks**: `scripts/gate_all.sh` (or dedicated CI gate wrapper)
- **Runtime behavior fence (Telegram)**: `_local/telegram_cp/guardrail.py` + `tg_cp_server.py` pre/post guard checks

### Policy ownership
- Policy text owner: `docs/skills/global_red_lines.md`
- Execution checks owner: `scripts/guardrail_check.sh` + CI gate
- Runtime safety owner: `_local/telegram_cp/guardrail.py`

## 3) Dedupe Actions (small, incremental)

### A. Docs (PR1, docs-only)
- Add this file and `docs/slimdown_plan_v2.md`.
- In future docs, reference `docs/skills/global_red_lines.md` instead of restating full rule text.

### B. Script enforcement (PR2 candidate)
- Extend `scripts/guardrail_check.sh` to include:
  - tg_cp no-exec scan for `_local/telegram_cp/tg_cp_server.py` (`subprocess|os.system|Popen`)
  - broader core protection check for full `src/hongstr/**`
  - staged `data/**` guard (state snapshots remain untracked runtime files)

### C. CI consistency (PR2/PR3 candidate)
- Align `scripts/gate_all.sh` protected path logic with `global_red_lines` (`src/hongstr/**`, not only subfolders).
- Keep PR template as declaration-only; treat script checks as source of pass/fail truth.

## 4) Verification Commands

```bash
# core unchanged
git diff --name-only origin/main...HEAD | rg '^src/hongstr/' && exit 1 || true

# tg_cp no-exec invariant
rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py && exit 1 || true

# no staged runtime artifacts
git status --porcelain | rg '^.. data/' && exit 1 || true

# local tg_cp smoke
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
```

## 5) Rollback

```bash
git revert <merge_commit_sha>
```

