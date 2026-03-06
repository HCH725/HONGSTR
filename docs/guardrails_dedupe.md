# Guardrails Dedupe Plan (Single-SSOT Policy)

Last updated (UTC): 2026-03-06T00:00:00Z
Status: migration log only. This file is not a canonical policy source.

## 1) Canonical Governance Sources

Use these docs as canonical by domain:

- repo-wide red lines: [`docs/skills/global_red_lines.md`](/Users/hong/Projects/HONGSTR/docs/skills/global_red_lines.md)
- agent event fields and vocabulary: [`docs/architecture/agent_event_schema_v1.md`](/Users/hong/Projects/HONGSTR/docs/architecture/agent_event_schema_v1.md)
- escalation targets, repair classes, cooldown/dedupe: [`docs/architecture/escalation_taxonomy_v1.md`](/Users/hong/Projects/HONGSTR/docs/architecture/escalation_taxonomy_v1.md)
- legacy Keep / Merge / Kill decisions: [`docs/architecture/legacy_keep_kill_merge_review_v1.md`](/Users/hong/Projects/HONGSTR/docs/architecture/legacy_keep_kill_merge_review_v1.md)
- Obsidian / LanceDB sidecar boundary: [`docs/ops/obsidian_lancedb_sop_appendix_v1.md`](/Users/hong/Projects/HONGSTR/docs/ops/obsidian_lancedb_sop_appendix_v1.md)

Rule:

- edit the canonical doc for new policy
- keep this file as evidence of dedupe work and enforcement ownership only

## 2) Current Guardrail Sources (and overlap)

| Layer | Source | Evidence | Current role | Overlap / issue |
|---|---|---|---|---|
| Policy SSOT | `docs/skills/global_red_lines.md` | `docs/skills/global_red_lines.md:1-23` | Canonical non-negotiables for all agents. | Correct source; should be referenced, not re-written repeatedly. |
| PR authoring | `.github/pull_request_template.md` | `.github/pull_request_template.md:13-19` | Requires safety statement in PR body. | Duplicates wording with docs; no machine enforcement. |
| Local guardrail script | `scripts/guardrail_check.sh` | `scripts/guardrail_check.sh:23-31` | Blocks core-path changes and artifact commits. | Does not enforce tg_cp no-exec regex, report_only stance, or Telegram-only policy. |
| CI/ops gate | `scripts/gate_all.sh` | `scripts/gate_all.sh:255-276` | Detects protected path touches during gate run. | Protection scope is narrower (`backtest/`, `execution/`) than full `src/hongstr/**`. |
| tg_cp runtime guard | `_local/telegram_cp/tg_cp_server.py` guard paths | `_local/telegram_cp/tg_cp_server.py` | Runtime refusal of action/execution intents in Telegram plane. | Strong runtime fence, but separate from git/CI checks. |
| Planning docs | `docs/slimdown_inventory.md`, `docs/slimdown_plan.md` | `docs/slimdown_inventory.md:3-9`, `docs/slimdown_plan.md:90-93` | Process guidance and checklist. | Repeated rule text causes drift risk across documents. |

## 3) Single-SSOT Guardrail Model

### Canonical source of truth
- Keep policy text in the domain-specific canonical docs listed above.
- Do not add new normative rule paragraphs here unless they are immediately moved into a canonical doc.

### Enforcement mapping
- **Authoring-time reminder**: `.github/pull_request_template.md`
- **Local preflight hard checks**: `scripts/guardrail_check.sh`
- **CI/merge hard checks**: `scripts/gate_all.sh` (or dedicated CI gate wrapper)
- **Runtime behavior fence (Telegram)**: `_local/telegram_cp/tg_cp_server.py` guard paths

### Policy ownership
- Policy text owner: `docs/skills/global_red_lines.md`
- Execution checks owner: `scripts/guardrail_check.sh` + CI gate
- Runtime safety owner: `_local/telegram_cp/tg_cp_server.py`

## 4) Dedupe Map (reference migration)

| Document | Previous state | Current state |
|---|---|---|
| `docs/slimdown_inventory.md` | Repeated full red-line bullet list | Replaced with policy SSOT reference |
| `docs/slimdown_phase3_backlog.md` | Repeated red-line scope block | Replaced with policy SSOT reference |
| `docs/slimdown_next_round.md` | Repeated red-line checklist | Replaced with policy SSOT reference |
| `docs/slimdown_launchd_planes.md` | Implicit policy assumptions | Added explicit policy SSOT reference |

Update rule:
- if policy wording changes, update only `docs/skills/global_red_lines.md`,
- then update references/anchors in dependent docs if paths or sections move.

## 5) Dedupe Actions (small, incremental)

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

## 6) Verification Commands

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

## 7) Rollback

```bash
git revert <merge_commit_sha>
```
