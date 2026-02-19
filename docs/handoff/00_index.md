# Handoff Index

**Last Updated**: 2026-02-18

## Recommended Reading Order

1. `01_system_overview.md`
2. `02_repo_map.md`
3. `03_workflows_runbook.md`
4. `04_artifacts_schema.md`
5. `09_codex_bootstrap.md`
6. `06_known_issues.md`
7. `07_decisions_and_rationales.md`
8. `17_rerun_workflow.md`

## Gate Policy (single source of truth)

- `13_gate_policy.md`

## One command to verify

```bash
bash scripts/gate_all.sh
```

Expected baseline behavior:

- Gate produces `reports/gate_latest.md`
- `WARN` is allowed
- Stop condition applies only to `FAIL`/`FATAL`
