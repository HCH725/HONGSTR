# Recommended Labels for HONGSTR Issues & PRs

Apply these labels to all Issues and PRs so the dispatcher, self-heal, and CI workflows can filter correctly.

## Core Labels

| Label        | Color     | When to Apply |
|--------------|-----------|---------------|
| `prd`        | `#0052cc` | Problem / requirements document issues |
| `epic`       | `#6f42c1` | Scope-defining parent issues |
| `task`       | `#1d76db` | Agent-dispatchable implementation units |
| `docs-only`  | `#bfd4f2` | Changes confined to `docs/**`, `*.md`, templates |
| `ops`        | `#e4e669` | Operational scripts, launchd, watchdog |
| `selfheal`   | `#e11d48` | Auto-triggered fix from monitoring alert |
| `research`   | `#0e8a16` | Research/ML changes; must be `report_only: true` |

## Allowed-Path Labels

These signal to the dispatcher which path set is in scope:

| Label            | Implied Paths |
|------------------|---------------|
| `allowed_paths:scripts` | `scripts/**` |
| `allowed_paths:docs`    | `docs/**`, `*.md` |
| `allowed_paths:web`     | `web/**` |
| `allowed_paths:research`| `research/**` |

> [!IMPORTANT]
> The `allowed_paths:` field in the issue template body is authoritative for the dispatcher.
> Labels are supplementary hints for human reviewers only.

## Priority Labels

| Label     | Meaning |
|-----------|---------|
| `P0`      | Production incident / data integrity at risk |
| `P1`      | High-priority, blocking other work |
| `P2`      | Normal priority |
| `P3`      | Nice-to-have, can defer |

## Label Hierarchy Rule

Every issue should have **exactly one** of: `prd`, `epic`, or `task`.  
Combine freely with domain labels (`ops`, `research`, `docs-only`) and priority labels.

## Creating Labels via CLI

```bash
gh label create prd        --color 0052cc --description "Product Requirements Document"
gh label create epic       --color 6f42c1 --description "Epic scope issue"
gh label create task       --color 1d76db --description "Agent-dispatchable task"
gh label create docs-only  --color bfd4f2 --description "Docs/template changes only"
gh label create ops        --color e4e669 --description "Operational scripts and infra"
gh label create selfheal   --color e11d48 --description "Auto-triggered remediation"
gh label create research   --color 0e8a16 --description "Research / report-only changes"
```
