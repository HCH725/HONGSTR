# L2 Self-Heal

Status: bounded non-Telegram ingress / keep-for-now under ingress review
Reference: `docs/architecture/legacy_dispatcher_ingress_review_v1.md`

## Definition
L2 Self-Heal = auto open PR + request review + never auto-merge + strict allowed_paths + required checks.

## Hard red lines
- No changes under src/hongstr/
- No subprocess/os.system/Popen in tg_cp
- No committing data/**, logs/**, parquet/pkl, or artifacts
- No policy auto-activation that changes trading semantics

## Trigger
Issue comment contains: /selfheal
Comment body must include a JSON Repair Ticket.

## Repair Ticket JSON schema (minimum)
{
  "title": "Fix <short>",
  "allowed_paths": ["docs/", "scripts/", "_local/telegram_cp/"],
  "problem": "...",
  "expected": "...",
  "repro": ["..."],
  "must_run": ["scripts/guardrail_check.sh", "python -m pytest _local/telegram_cp/test_local_smoke.py"],
  "notes": "..."
}

## Required checks
- scripts/guardrail_check.sh
- python -m pytest _local/telegram_cp/test_local_smoke.py

## Governance
- PR must be Draft
- PR must request review
- No auto-merge
