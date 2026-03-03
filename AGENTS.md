# HONGSTR Agents (OpenCode)

## Default agent: hongstr-safe (use for ALL chats in this repo)

### Always-on rules (non-negotiable)
- **No silent local edits**: any change must end as a PR (commit -> push -> PR).
- **Core diff=0**: do NOT change core semantics under `src/hongstr/` unless explicitly approved.
- **tg_cp is no-exec**: do NOT propose `subprocess`, `os.system`, `Popen`, or shell-out in tg_cp/control-plane.
- **No artifacts committed**: never commit `data/**`, `reports/**`, `tmp/**`, `_local/**` artifacts.
- **SSOT-only for system status**: read `data/state/*.json` (health/freshness/coverage/brake/regime/daily), never recompute.

### Default behavior
- Planning-first: provide plan + commands. Assume **no-write** unless user explicitly says "apply/modify".
- Shell: macOS/zsh-safe commands; avoid brittle `set -euo pipefail`; avoid risky globs.

### Skills to enable
- hongstr-guardrails
- hongstr-plan-only
- hongstr-safe-shell
- hongstr-ssot-only
