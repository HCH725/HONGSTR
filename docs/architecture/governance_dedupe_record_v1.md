# HONGSTR Governance Dedupe Record v1

Last updated: 2026-03-06 (UTC+8)
Status: docs-only / migration ledger / no runtime wiring
Stage: Stage 2 / Stage 7 / Stage 8
Checklist item: governance dedupe + dispatcher sandbox/archive-only
Plane: Governance docs spanning State Plane / Control Plane / Research Plane
Expected SSOT/output impact: none

## 0. Purpose

This file records which governance docs are canonical, which older docs were downgraded, and which legacy multi-entry assets are removal candidates.

This file is a migration ledger, not a second policy source.

## 1. Canonical Docs

| Domain | Canonical doc | Why |
|---|---|---|
| Agent roles, planes, single Telegram entrance | `docs/architecture/agent_organization_governance_v1.md` | Umbrella overview for Stage 2 / 7 / 8 governance |
| Event fields and vocabulary | `docs/architecture/agent_event_schema_v1.md` | Canonical event payload contract |
| Escalation targets, repair classes, cooldown/dedupe | `docs/architecture/escalation_taxonomy_v1.md` | Canonical routing and suppression policy |
| Legacy Keep / Merge / Kill decisions | `docs/architecture/legacy_keep_kill_merge_review_v1.md` | Canonical path/module disposition |
| Legacy dispatcher ingress audit and removal sequencing | `docs/architecture/legacy_dispatcher_ingress_review_v1.md` | Canonical inventory and classification for non-Telegram ingress review |
| Obsidian / LanceDB sidecar boundary | `docs/ops/obsidian_lancedb_sop_appendix_v1.md` | Canonical sidecar boundary and kill switch |

## 2. Docs Downgraded In This PR

| Path | New status | Reason |
|---|---|---|
| `docs/guardrails_dedupe.md` | migration log | keeps enforcement ownership and dedupe evidence, but no longer defines canonical policy text |
| `docs/obsidian_lancedb.md` | compatibility note | keeps implementation commands, but sidecar policy moved to the appendix |
| `docs/dispatcher_agent.md` | archive-only / sandbox-only / deprecated | documents a legacy non-Telegram operator ingress |
| `docs/governance/ccpm_adoption.md` | historical note | `/dispatch` workflow references are no longer the target governance model |

## 3. Content Merged Into Canonical Docs

| Former duplicated topic | Canonical destination |
|---|---|
| event field definitions and routing | `docs/architecture/agent_event_schema_v1.md` |
| escalation targets, bounded repair, cooldown, dedupe | `docs/architecture/escalation_taxonomy_v1.md` |
| Keep / Merge / Kill decisions for dispatcher and sidecar paths | `docs/architecture/legacy_keep_kill_merge_review_v1.md` |
| Obsidian / LanceDB truth-source boundary | `docs/ops/obsidian_lancedb_sop_appendix_v1.md` |

## 4. Legacy Multi-Entry Inventory

These paths either already form, or document, operator-triggered entrypoints outside Telegram.

| Path | Current status | This PR action | Next step |
|---|---|---|---|
| `docs/dispatcher_agent.md` | archive-only | downgraded and linked to canonical docs | remove candidate |
| `docs/dispatcher_smoke.md` | archive-only artifact | downgraded to historical smoke note | remove candidate |
| `scripts/dispatch/dispatch_issue.sh` | legacy alternate ingress | recorded only; runtime unchanged | removal candidate in a later smallest-unit PR |
| `.github/workflows/dispatch.yml` | legacy alternate ingress | recorded only; workflow unchanged | removal candidate in a later smallest-unit PR |
| `.github/ISSUE_TEMPLATE/task.yml` | historical dispatch template | recorded only; template unchanged | deprecate/remove with dispatcher retirement |
| `docs/self_heal.md` | bounded legacy issue-comment repair path | recorded only; out of scope for this PR | later review candidate because it is a non-Telegram ingress even though it is bounded |

## 5. Stage Alignment

### Stage 2

- keep `scripts/refresh_state.sh` -> `scripts/state_snapshots.py` as the only canonical SSOT refresh/publish chain
- keep `/status`, `/daily`, and `/dashboard` deterministic and SSOT-only
- keep missing/unreadable SSOT degradation at `UNKNOWN` + `refresh_hint`

### Stage 7

- keep Telegram as the single outward operator entrance
- treat GitHub issue-comment dispatch paths as legacy/sandbox only, not as current target governance
- keep top-level reporting read-only

### Stage 8

- keep Obsidian / LanceDB as report-only or retrieval sidecars
- keep cooldown/dedupe policy in the escalation taxonomy, not scattered across multiple docs
- keep bounded repair PR-based and allowlist-only

## 6. Degrade / Kill Switch / Removal Plan

Degrade:

- this PR only changes doc authority and status labels
- if any downgrade is premature, keep the historical doc but continue treating canonical docs as authoritative

Kill switch:

- close the stacked PR or revert the docs commit
- current runtime behavior remains unchanged because no workflow or script wiring was modified

Removal plan:

1. keep historical docs and workflows frozen
2. retire dispatcher-related runtime/assets in a later smallest-unit PR
3. remove or archive dependent templates and smoke artifacts in the same retirement slice
4. keep final authority in the canonical docs listed above

## 7. Out Of Scope / Not Changed

- `src/hongstr/**`
- any canonical `data/state/*` writer or consumer
- `_local/telegram_cp/tg_cp_server.py`
- `scripts/dispatch/dispatch_issue.sh`
- `.github/workflows/dispatch.yml`
- `.github/ISSUE_TEMPLATE/task.yml`
- any Telegram, Obsidian, LanceDB, mirror, or SSOT runtime wiring
