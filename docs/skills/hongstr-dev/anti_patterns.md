# Anti-patterns (Engineering)

**MUST READ FIRST:** `docs/skills/global_red_lines.md`

- Do NOT modify `src/hongstr/**`.
- Do NOT commit artifacts under `data/**`.
- Do NOT add exec/remediation to tg_cp (no subprocess/os.system/Popen).
- Do NOT do “large refactor + unrelated bugfix” in the same PR.
- Do NOT change trading/execution semantics based on research output.
