# Example 1: Ops / Self-Heal Bugfix

## Context

The `tg_cp_watchdog` launchd plist was using `$HOME` in the log path, which macOS launchd
does not expand — causing the watchdog to silently write to the wrong location.

---

## PRD (Issue: prd label)

**Problem Statement:**
`StandardOutPath` in `ops/launchagents/com.hongstr.tg_cp_watchdog.plist` uses `$HOME` which
launchd does not expand at runtime. Logs are not written to the expected path.

**Non-goals:**

- Not changing any Python code or TG bot logic.
- Not modifying monitoring thresholds.

**Acceptance Criteria:**

```
AC1: bash scripts/guardrail_check.sh → exits 0
AC2: git diff origin/main...HEAD -- src/hongstr | wc -l → 0
AC3: ops/launchagents/com.hongstr.tg_cp_watchdog.plist contains no $HOME references
AC4: docs/tg_cp_watchdog.md documents the absolute path requirement
```

**Risk:** Low — ops config only, no runtime code changed.

**Rollback:** `git revert <merge_commit>`

---

## Epic (Issue: epic label, refs PRD)

**Scope:**

```
ops/launchagents/com.hongstr.tg_cp_watchdog.plist
docs/tg_cp_watchdog.md
```

**allowed_paths:**

```
allowed_paths:
  - ops/launchagents/com.hongstr.tg_cp_watchdog.plist
  - docs/tg_cp_watchdog.md
```

**Workstreams:**

```
WS-A: Fix plist paths
WS-B: Update deployment docs
```

(Both can be done in one PR since they are coupled and low-risk.)

**Gates:**

```
GATE-1: bash scripts/guardrail_check.sh exits 0
GATE-2: grep -r '\$HOME' ops/launchagents/ → empty
GATE-3: PR approved by maintainer
```

---

## Task (Issue: task label, refs Epic)

**allowed_paths:**

```
allowed_paths:
  - ops/launchagents/com.hongstr.tg_cp_watchdog.plist
  - docs/tg_cp_watchdog.md
```

**Checklist:**

```
- [ ] Replace $HOME with absolute path in StandardOutPath
- [ ] Replace $HOME with absolute path in StandardErrorPath
- [ ] Update docs/tg_cp_watchdog.md install section
- [ ] Run bash scripts/guardrail_check.sh
- [ ] Confirm grep -r '$HOME' ops/launchagents/ is empty
```

**Tests:**

```bash
bash scripts/guardrail_check.sh
git diff origin/main...HEAD -- src/hongstr | wc -l   # must be 0
grep -r '\$HOME' ops/launchagents/                   # must be empty
```

**Rollback:** `git revert <pr_merge_sha>`

**Flags:** ☐ docs-only  ☐ report_only  ☑ ops
