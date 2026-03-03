# Dispatcher Agent SOP

Phase 2B extends `/dispatch` so an allowlisted issue comment can run a guarded LLM-backed patch flow.
The default provider is local Ollama, so the runner does not need an OpenAI API key for the standard path.

## Issue Template

Use this issue-body shape when you want the dispatcher to run in agent mode:

```text
Allowed paths:
- docs/dispatcher_smoke.md
Agent: codex
Task:
- Update docs/dispatcher_smoke.md with a short verification note
```

If `Agent:` is omitted, the dispatcher keeps the existing smoke-stub behavior.
`Task:` and `Agent plan:` are both accepted as the task section heading.
The default model is `qwen2.5-coder:7b-instruct` through `OLLAMA_MODEL`.
If you need a prose-oriented fallback on the runner, override `OLLAMA_MODEL=qwen2.5:7b-instruct`.

## Manual E2E Recipe

1. Create an issue using the template above.
2. Keep the `Allowed paths` list limited to the files you want the runner to touch.
3. Comment `/dispatch` as an allowlisted owner.
4. Confirm the workflow posts an acknowledgement comment.
5. Confirm the workflow opens a draft PR.
6. Confirm the PR diff is limited to the `Allowed paths` list.
7. Confirm the issue thread receives a concise PR URL comment.

## Common Failures

- Missing `Allowed paths`
  The issue will be marked blocked and the thread will receive the exact template:
  `Allowed paths:`
  `- docs/dispatcher_smoke.md`

- `allowed_paths_diff_gate` blocked
  The generated patch or final git diff touched a path outside the allowlist. Tighten the task or widen `Allowed paths` before retrying.

- Budget gate blocked
  The estimated or actual model spend exceeded `MAX_COST_USD` or `MAX_TOKENS`. Reduce task scope or raise the workflow budget.

- Missing `OPENAI_API_KEY`
  This only applies when you explicitly switch `AGENT_PROVIDER=openai`. The default Ollama path does not require an API key.

- Draft PR creation blocked
  The runner finished patch generation but could not open the PR because of permissions or branch policy. Check the issue comment for the Actions run link and fix the GitHub-side restriction.

## Rollback

Use `git revert <commit_sha>` on the merge commit if the feature needs to be backed out.
