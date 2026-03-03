# Global Red Lines (SSOT)

These rules are non-negotiable and apply to **ALL** agents (coding, research, control-plane).

## Stability-first
- **Do NOT change** `src/hongstr/**` core semantics. (core diff=0)
- Any ML/Research integration must be **report_only** by default.

## Repo hygiene / artifacts
- **Do NOT commit** generated artifacts under `data/**` (parquet/pkl/jsonl/backtest runs, etc).
- `data/state/*.json` are runtime state snapshots and must remain **untracked** in git.

## tg_cp / Telegram control plane
- `tg_cp` is **strictly read-only**:
  - No `subprocess`, no `os.system`, no `Popen`, no arbitrary shell.
  - No auto-fix that writes code or executes remediation.
- Telegram is the only notification channel; keep current chat allowlist policy.

## GitHub SSOT process
- GitHub is the single source of truth:
  - Every change must be **commit + push + PR**.
  - Use Plan B on local machine: `gh` + `scripts/gh_pr_merge.sh`.
- Rollback via `git revert <commit_sha>`.

