# HONGSTR Legacy Keep / Kill / Merge Review v1

Last updated: 2026-03-06 (UTC+8)  
Status: docs-only / governance review / no runtime wiring  
Stage: Stage 2 / Stage 7 / Stage 8  
Checklist item: Legacy Keep / Kill / Merge Review v1  
Plane: State Plane + Control Plane + Research Plane legacy inventory  
Expected SSOT/output impact: none

## 0. Review Rule

This review classifies existing paths and modules into:

- `Keep`: retain as part of the target architecture
- `Merge`: keep temporarily, but converge ownership or documentation into a smaller canonical set
- `Kill`: freeze from the target roadmap and plan removal or sandbox-only containment

The review is policy-first. It does not modify runtime in this PR.

## 1. Keep

| Path or module | Decision | Why it stays | Stage alignment |
|---|---|---|---|
| `scripts/refresh_state.sh` | Keep | Canonical operator entrypoint for SSOT refresh; preserves deterministic fallback through `refresh_hint`. | Stage 2 |
| `scripts/state_snapshots.py` | Keep | Single canonical writer for `data/state/*`; must remain unique. | Stage 2 |
| `scripts/check_state_writer_boundary.py` | Keep | Existing guardrail anchor for the single-writer boundary. | Stage 2 |
| `ops/launchagents/com.hongstr.refresh_state.plist` | Keep | Scheduler owner for the state-plane refresh chain. | Stage 2 |
| `docs/ops/telegram_operator_manual.md` | Keep | Documents `/daily` as SSOT-only and deterministic. | Stage 2 / Stage 7 |
| `docs/ops/daily_report_single_entry.md` | Keep | Keeps `/daily` tied to `data/state/daily_report_latest.json`. | Stage 2 / Stage 7 |
| `_local/telegram_cp/tg_cp_server.py` | Keep | Single Telegram outward entrance; keep read-only posture and no arbitrary exec. | Stage 7 |
| `ops/launchagents/com.hongstr.tg_cp.plist` | Keep | Single production Telegram daemon anchor. | Stage 7 |
| `scripts/notify_telegram.sh` | Keep | Utility stays, but ownership remains with the steward path only, not specialists. | Stage 7 |
| `research/loop/research_loop.py` | Keep | Explicit `report_only` behavior and `actions=[]` already match Stage 8. | Stage 8 |
| `scripts/poll_research_loop.sh` | Keep | Existing cooldown/dedupe wrapper is consistent with report-only scheduling. | Stage 8 |
| `ops/launchagents/com.hongstr.research_poller.plist` | Keep | Queue/cooldown scheduler should stay separated from control-plane reporting. | Stage 8 |
| `scripts/obsidian_sync.py` | Keep | Sidecar exporter is acceptable if it remains non-authoritative. | Stage 8 |
| `scripts/obsidian_lancedb_index.py` | Keep | Retrieval index is acceptable as knowledge sidecar only. | Stage 8 |
| `scripts/obsidian_lancedb_query.py` | Keep | Retrieval helper is acceptable if it never becomes top-level status truth. | Stage 8 |
| `scripts/obsidian_rag_run.sh` | Keep | Sidecar context assembly is acceptable if it remains report-only and optional. | Stage 8 |
| `scripts/auto_pr.sh` | Keep with boundary | Useful for small allowlisted report/docs flows; must never become a Telegram-triggered runtime executor. | Stage 8 / global PR-as-smallest-unit |

## 2. Merge

| Path or module | Decision | Merge target | Why merge is needed | Removal plan |
|---|---|---|---|---|
| `ops/launchagents/com.hongstr.daily_healthcheck.plist` | Merge | `ops/launchagents/com.hongstr.refresh_state.plist` ownership | Health/state scheduling must converge on one canonical state-plane owner. | Keep as alias-only now, then retire duplicate schedule after observation window. |
| `docs/architecture/agent_organization_governance_v1.md` | Merge | `docs/architecture/agent_event_schema_v1.md` and `docs/architecture/escalation_taxonomy_v1.md` as normative event/escalation references | Existing governance doc is broad; event/escalation rules should stop drifting across documents. | Keep as umbrella overview, replace duplicated normative sections with links. |
| `docs/architecture/legacy_dispatcher_ingress_review_v1.md` | Merge | detailed ingress inventory for dispatcher and non-Telegram execution paths | direct ingress retirement needs a narrower audit than this broad legacy review | Keep as detailed audit reference while broad legacy review remains summary-level |
| `docs/guardrails_dedupe.md` | Merge | `docs/architecture/escalation_taxonomy_v1.md` for suppression rules, plus policy SSOT references | Cooldown/dedupe guidance should sit next to escalation routing instead of floating separately. | Keep evidence table, trim normative policy later. |
| `docs/obsidian_lancedb.md` | Merge | `docs/ops/obsidian_lancedb_sop_appendix_v1.md` plus sidecar boundary references | Sidecar boundary language should converge to one canonical statement to reduce truth-source drift. | Keep compatibility notes, move policy wording to one source later. |
| `ops/launchagents/com.hongstr.research_loop.plist` | Merge | `ops/launchagents/com.hongstr.research_poller.plist` scheduling ownership split | The repo should keep one queue/cooldown owner and one execution target, not two competing schedulers. | Preserve one-shot executor, remove duplicate schedule ownership in a later small PR. |

## 3. Kill

| Path or module | Decision | Why it conflicts with target architecture | Kill switch / containment | Removal plan |
|---|---|---|---|---|
| `docs/dispatcher_agent.md` | Kill from production roadmap | It defined an alternate operator-triggered agent execution surface outside the Telegram single-entry model. | Retired by `docs/architecture/direct_dispatch_retirement_v1.md`. | Removed now; preserve history in retirement/audit docs only. |
| `scripts/dispatch/dispatch_issue.sh` | Kill from production roadmap | It created a second outward control path for task execution, which conflicts with Stage 7 single-entry governance even if allowlisted. | Retired by `docs/architecture/direct_dispatch_retirement_v1.md`. | Removed now with the direct `/dispatch` workflow and task template. |
| `.github/workflows/dispatch.yml` | Kill from production roadmap | It allowed GitHub issue comments to act as a second operator ingress. | Retired by `docs/architecture/direct_dispatch_retirement_v1.md`. | Removed now with the direct `/dispatch` chain. |
| `.github/ISSUE_TEMPLATE/task.yml` | Kill from production roadmap | It actively framed GitHub tasks as dispatchable through `/dispatch`. | Retired by `docs/architecture/direct_dispatch_retirement_v1.md`. | Removed now with the direct `/dispatch` chain. |
| `docs/dispatcher_smoke.md` | Kill from production roadmap | It existed only as a support artifact for the retired direct dispatcher flow. | Retired by `docs/architecture/direct_dispatch_retirement_v1.md`. | Removed now with the direct `/dispatch` chain. |

## 4. Explicit Non-Negotiable Keep-But-Do-Not-Expand List

These existing modules stay only if their boundaries do not expand:

- `_local/telegram_cp/tg_cp_server.py`: keep as read-only control-plane entrance; do not add arbitrary execution
- `scripts/notify_telegram.sh`: keep as steward-owned notification helper; do not grant direct specialist ownership
- `scripts/obsidian_sync.py`, `scripts/obsidian_lancedb_index.py`, `scripts/obsidian_lancedb_query.py`, `scripts/obsidian_rag_run.sh`: keep as optional sidecars; do not connect them to `/status` or `/daily`
- `scripts/auto_pr.sh`: keep as PR helper; do not turn it into a hidden runtime mutation path

## 5. Forbidden Expansion List

The following expansions are forbidden even if the underlying path is otherwise kept:

- expanding `_local/telegram_cp/tg_cp_server.py` into a free-form coding-agent executor
- allowing `scripts/state_snapshots.py` or `scripts/refresh_state.sh` to share canonical ownership with any new writer
- letting `scripts/obsidian_sync.py` or `scripts/obsidian_lancedb_query.py` feed canonical status truth
- reviving `scripts/dispatch/dispatch_issue.sh` as a production operator ingress

## 6. Degrade / Kill Switch / Incremental Adoption

Degrade:

- this review changes no runtime behavior
- if any decision proves too aggressive, keep the path frozen in docs and revisit in a later smallest-unit PR

Kill switch:

- close the stacked PR or revert the docs commit
- keep current runtime unchanged until a later allowlisted implementation PR lands

## 7. Recommended Next Removal / Merge Sequence

1. keep `com.hongstr.refresh_state` as the only canonical state-plane owner and retire duplicate schedule semantics under `com.hongstr.daily_healthcheck`
2. replace duplicated event/escalation wording in broad governance docs with links to the new v1 schema/taxonomy docs
3. keep the direct `/dispatch` chain retired and do not reintroduce GitHub issue-comment execution as a production ingress
4. keep Obsidian/LanceDB as sidecar-only and refuse any proposal that promotes them to control-plane truth
