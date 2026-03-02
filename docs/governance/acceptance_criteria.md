# How to Write Acceptance Criteria (AC) for HONGSTR

AC in HONGSTR must be **binary**, **machine-verifiable**, and **traceable** to a test or guardrail.

---

## Format

Each criterion follows this pattern:

```
AC<N>: <command or observable> → <expected outcome>
```

Examples:

```
AC1: bash scripts/guardrail_check.sh → exits 0
AC2: git diff origin/main...HEAD -- src/hongstr | wc -l → 0
AC3: cat data/state/system_health_latest.json | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['ssot_status']=='OK'" → passes
AC4: [docs-only] All changed file extensions are .md or .yml → verified by reviewer
```

---

## Rules

1. **Binary**: Either passes or fails. "Should probably work" is not an AC.
2. **Traceable**: Each AC maps to a command (automated) or a specific manual check.
3. **Minimal**: 3–6 ACs per task. Too many ACs = task is too broad, split it.
4. **Scoped to the task**: Do not copy-paste all global guardrail ACs; only include what the task actually changes.

---

## Mandatory ACs for All PRs

These are always required (from the global guardrail):

```
AC_GLOBAL_1: bash scripts/guardrail_check.sh → exits 0
AC_GLOBAL_2: git diff origin/main...HEAD -- src/hongstr | wc -l → 0
AC_GLOBAL_3: git ls-files | rg '\.(parquet|pkl)$' → empty
```

---

## How ACs Map to PR Body

When a Task Issue is dispatched, the agent surfaces the `acceptance_criteria:` field into the PR body under a `## Acceptance Criteria` section.

The reviewer can then verify each AC before approving the PR.

---

## AC for Different Task Types

| Task Type    | Minimum Additional ACs |
|--------------|------------------------|
| `docs-only`  | Reviewer manual check: all diffs confined to `docs/**` or `.github/**` |
| `ops`        | Specific command/launchctl output check |
| `research`   | `report_only: true` in modified files; no `os.system/subprocess` added |
| `selfheal`   | Root cause confirmed; existing test that would have caught the bug |
