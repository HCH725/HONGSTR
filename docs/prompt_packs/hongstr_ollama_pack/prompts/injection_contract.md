Injection Contract (docs-only)

Goal: build a single system message per request.

Order
1) base_system_prompt.md
2) model overlay (one of the overlay_*.md)
3) selected skills (allowlisted, relevant only)
4) SSOT snapshot (short, safe, redacted)
5) stable block templates (only if needed)

Rules
- Keep context minimal; inject only what is needed.
- Never inject secrets or raw environment values.
- If SSOT is missing/unreadable, degrade gracefully to UNKNOWN and suggest refresh_state.
