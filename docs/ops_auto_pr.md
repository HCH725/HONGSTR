# Auto-PR Operations (Phase B -> C)

`scripts/auto_pr.sh` is a guardrailed automation helper for report-only paths.

## Safety Defaults

- Default mode: create **draft PR** only (no auto-merge).
- Auto-merge is allowed only when both conditions hold:
  - change class is `docs-only`
  - `--allow-docs-automerge` is explicitly set
- Guardrails:
  - allowlist only: `docs/**`, `_local/**`, `research/**`, `scripts/**`
  - blocked: `src/hongstr/**`, `data/**`

## Commands

```bash
# Standard run (sync main, classify changes, preflight, open draft PR)
bash scripts/auto_pr.sh

# Explicit draft flag (same effect as default)
bash scripts/auto_pr.sh --draft

# Allow docs-only auto-merge (explicit)
bash scripts/auto_pr.sh --allow-docs-automerge

# Run named generator via AUTO_PR_GENERATORS mapping + --only selector
AUTO_PR_GENERATORS='regime_thresholds_calibration:bash scripts/calibrate_regime_thresholds.sh --pr-mode --as-of-utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"' \
  bash scripts/auto_pr.sh --draft --only regime_thresholds_calibration --print-next-steps

# Skip preflight (not recommended)
bash scripts/auto_pr.sh --skip-preflight
```

## Cooldown / Dedupe

- State file: `_local/auto_pr/state.json`
- Behavior:
  - if same change class + same fingerprint is seen within cooldown window, auto_pr exits 0 without opening another PR.
  - cooldown skip log now includes:
    - human-readable remaining time (`Xd Xh Xm Xs`)
    - latest open PR URL for the same class prefix (`codex/auto-pr-<kind>-*`) when found via `gh pr list`
    - fallback hint when no open PR is found:
      - `No open PR found; rerun after cooldown or use --cooldown-hours 0 (if operator chooses).`
- Cooldown setting:

```bash
AUTO_PR_COOLDOWN_HOURS=24 bash scripts/auto_pr.sh
```

## Operator Next Steps (Printed Only)

Use `--print-next-steps` to print suggested follow-up commands without executing them:

```bash
gh pr ready <n>                # printed only when PR is draft
gh pr checks <n> --watch
gh pr merge <n> --squash --delete-branch
```

## Example Transcript

```bash
[auto_pr] Syncing main ...
[auto_pr] Running generators ...
[auto_pr] Changed files:
  - docs/governance/overfit_gates_aggressive.md
  - docs/governance/overfit_weekly_checklist.md
[auto_pr] Classified change: docs-only
[codex/auto-pr-docs-only-20260226_191500 abcdef1] docs(auto_pr): refresh docs
 2 files changed, 55 insertions(+)
[auto_pr] PR created: https://github.com/HCH725/HONGSTR/pull/XXX
[auto_pr] done
```

## Rollback

After merge:

```bash
git revert <merge_commit_sha>
```
