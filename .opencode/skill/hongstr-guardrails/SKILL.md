---
name: hongstr-guardrails
description: Enforce HONGSTR red lines: core diff=0, tg_cp no-exec, no artifact commits, PR-based workflow.
compatibility: opencode
---

## Non-negotiable red lines
- Do NOT change core semantics under `src/hongstr/` unless user explicitly approves.
- tg_cp/control-plane is **no-exec**: do not propose `subprocess`, `os.system`, `Popen`, shelling out, etc.
- Never commit generated artifacts: `data/**`, `reports/**`, `tmp/**`, `_local/**`.
- Any change must follow: commit → push → PR (prefer docs-only PRs when possible).
- If a request could touch SSOT writers/state producers (`scripts/refresh_state.sh`, `scripts/state_snapshots.py`, `reports/state_atomic/*`), STOP and ask for confirmation.

## Required output format
1) Plan (1–5 bullets)
2) Commands (copy-paste)
3) What to paste back (exact outputs)
