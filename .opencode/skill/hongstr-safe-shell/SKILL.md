---
name: hongstr-safe-shell
description: Generate zsh/macOS-safe commands: avoid brittle strict mode, avoid risky globs, be idempotent, and provide clear fallbacks.
compatibility: opencode
---

## Shell safety rules (zsh/macOS)
- Avoid `set -euo pipefail` unless absolutely necessary.
- Avoid `|| exit 1` patterns in copy-paste blocks; prefer explicit checks and readable errors.
- Avoid unquoted globs; if needed, quote patterns or use `noglob`.
- Prefer idempotent commands and show what changed.
- If a command can fail harmlessly, append `|| true` and explain why.

## Required output format
1) Plan
2) Commands (copy-paste)
3) What to paste back

## Non-negotiable: command integrity
- When the user provides a command block to run, do **NOT** rewrite it.
- Only allowed actions:
  1) Ask user to confirm before running if risky, OR
  2) Provide a separate "Safer alternative" block clearly labeled, without altering the original.
- Never sneak in `|| exit 1`, shell substitutions, or extra pipes into the user's provided command.
