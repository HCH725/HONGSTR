# Skills Registry Schema (v1, docs-only)

Each skill is a read-only capability description that may be injected into model context.

Fields:
- id: stable identifier (snake_case)
- title: short human name
- purpose: why it exists
- inputs: list of named inputs and types
- outputs: list of outputs and types
- constraints: red-line notes (must be read-only, no code writes, no shell)
- ssot_sources: which data/state files it reads (if any)
- examples: 1-2 examples of usage
