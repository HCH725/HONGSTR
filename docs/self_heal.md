# L2 Self-Heal

Status: sandbox-only bounded repair note / non-canonical for production ingress
Canonical disposition: `docs/architecture/bounded_selfheal_disposition_v1.md`
Reference: `docs/architecture/legacy_dispatcher_ingress_review_v1.md`

This file describes the current workflow shape. It does not authorize `/selfheal` as a production operator entrance.

## Definition
L2 Self-Heal = auto open PR + request review + never auto-merge + strict allowed_paths + required checks.

## Hard red lines
- No changes under src/hongstr/
- No subprocess/os.system/Popen in tg_cp
- No committing data/**, logs/**, parquet/pkl, or artifacts
- No policy auto-activation that changes trading semantics

## Trigger
Current implementation accepts either:

- GitHub issue comment containing `/selfheal`
- GitHub `workflow_dispatch`

Both are non-Telegram ingress surfaces. Governance currently treats them as sandbox-only, not as part of the target single-entry production model.

## Repair Ticket JSON schema (minimum)
{
  "title": "Fix <short>",
  "allowed_paths": ["docs/", "scripts/self_heal/", "tests/test_self_heal_allowed_paths.py"],
  "problem": "...",
  "expected": "...",
  "repro": ["..."],
  "must_run": ["scripts/self_heal/run_required_checks.sh"],
  "notes": "..."
}

## Required checks
- bash scripts/self_heal/run_required_checks.sh

## Governance
- PR must be Draft
- PR must request review
- No auto-merge
- No expansion beyond sandbox-only bounded repair without a separate approved PR
