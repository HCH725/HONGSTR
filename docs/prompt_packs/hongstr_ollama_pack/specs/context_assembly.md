# Context Assembly Spec (v1)

Goal: assemble a single system message from:
- base_system
- model overlay
- red lines reference
- injected skills (selected from allowlist)
- SSOT snapshot (short)
- stable blocks templates (optional)

Rules:
- Prefer brevity: inject only what is needed for the current task.
- Never inject secrets or raw env values.
- If SSOT missing/unreadable, degrade to UNKNOWN + refresh hint.
