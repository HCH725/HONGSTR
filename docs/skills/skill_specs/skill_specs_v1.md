# Skill Specs v1 (Schema-Bound, SSOT-Only)

Policy SSOT: `docs/skills/global_red_lines.md`

This document is the canonical schema reference for:
- tg_cp Qwen system prompt skill responses
- Quant Specialist Reasoning Model reasoning responses

## Prompt Injection Contract (v1)

System prompts should include this compact contract summary and path reference:

- `Skill Specs (v1): docs/skills/skill_specs/skill_specs_v1.md`
- Responses must follow the matching schema for the requested skill.
- Evidence must be SSOT-only (rules below).

## SSOT-Only Evidence Rules (Strict)

- Allowed evidence sources:
  - `data/state/*.json` (canonical runtime SSOT)
  - `reports/*` artifacts that already exist
- Disallowed for top-level status reasoning in tg_cp:
  - scanning `data/derived/*`
  - scanning logs or tailing runtime files as status evidence
  - ad-hoc artifact discovery outside declared SSOT/report pointers
- Missing/unreadable SSOT input must degrade to:
  - status: `UNKNOWN`
  - hint: `bash scripts/refresh_state.sh`

## A) tg_cp Skill Schemas (Qwen)

All tg_cp schemas are read-only and must not contain executable actions.

### 1) morning_brief

```json
{
  "skill": "morning_brief",
  "window_utc": "<string>",
  "ssot_status": "OK|WARN|FAIL|UNKNOWN",
  "highlights": ["<string>"],
  "risks": ["<string>"],
  "next_checks": ["<string>"],
  "evidence": ["<path>#<key_or_note>"]
}
```

### 2) incident_timeline

```json
{
  "skill": "incident_timeline",
  "incident_id": "<string>",
  "status": "OPEN|MITIGATED|RESOLVED|UNKNOWN",
  "timeline": [
    {"ts_utc": "<string>", "event": "<string>", "source": "<path_or_note>"}
  ],
  "impact": "<string>",
  "evidence": ["<path>#<key_or_note>"]
}
```

### 3) config_drift

```json
{
  "skill": "config_drift",
  "status": "OK|WARN|FAIL|UNKNOWN",
  "drifts": [
    {"item": "<string>", "expected": "<string>", "observed": "<string>", "severity": "LOW|MEDIUM|HIGH"}
  ],
  "scope": ["<string>"],
  "evidence": ["<path>#<key_or_note>"]
}
```

### 4) freshness_watchdog

```json
{
  "skill": "freshness_watchdog",
  "status": "OK|WARN|FAIL|UNKNOWN",
  "max_age_h": "<number|null>",
  "non_ok_rows": "<integer>",
  "affected": ["<symbol_tf_or_component>"],
  "refresh_hint": "bash scripts/refresh_state.sh",
  "evidence": ["data/state/freshness_table.json#rows"]
}
```

### 5) execution_quality

```json
{
  "skill": "execution_quality",
  "status": "OK|WARN|FAIL|UNKNOWN",
  "quality_signals": ["<string>"],
  "degradations": ["<string>"],
  "constraints": ["read_only", "report_only"],
  "evidence": ["<path>#<key_or_note>"]
}
```

## B) Quant Specialist Skill Schemas (Reasoning Model)

All quant specialist outputs are `report_only` by default.

### 1) repro_audit

```json
{
  "skill": "repro_audit",
  "status": "OK|WARN|FAIL",
  "scope": "<string>",
  "findings": ["<string>"],
  "repro_gaps": ["<string>"],
  "evidence": ["<path>#<key_or_note>"]
}
```

### 2) factor_drift

```json
{
  "skill": "factor_drift",
  "status": "OK|WARN|FAIL",
  "drift_summary": ["<string>"],
  "candidate_causes": ["<string>"],
  "monitoring_suggestions": ["<string>"],
  "evidence": ["<path>#<key_or_note>"]
}
```

### 3) tcost_calibrator

```json
{
  "skill": "tcost_calibrator",
  "status": "OK|WARN|FAIL",
  "assumptions": ["<string>"],
  "calibration_notes": ["<string>"],
  "sensitivity": ["<string>"],
  "evidence": ["<path>#<key_or_note>"]
}
```

### 4) exposure_decomposition

```json
{
  "skill": "exposure_decomposition",
  "status": "OK|WARN|FAIL",
  "exposure_buckets": ["<string>"],
  "dominant_drivers": ["<string>"],
  "risk_flags": ["<string>"],
  "evidence": ["<path>#<key_or_note>"]
}
```

### 5) regime_sensitivity

```json
{
  "skill": "regime_sensitivity",
  "status": "OK|WARN|FAIL",
  "regime_cases": ["<string>"],
  "sensitivity_summary": ["<string>"],
  "stability_notes": ["<string>"],
  "evidence": ["<path>#<key_or_note>"]
}
```

### 6) lookahead_audit

```json
{
  "skill": "lookahead_audit",
  "status": "OK|WARN|FAIL",
  "audit_scope": "<string>",
  "violations": ["<string>"],
  "confidence": "LOW|MEDIUM|HIGH",
  "evidence": ["<path>#<key_or_note>"]
}
```

## Implementation Notes (Non-Behavioral)

- This file is schema/policy guidance only.
- Runtime behavior remains controlled by existing code paths and guardrails.
- Any runtime prompt assembly changes must preserve read-only + SSOT-only constraints and go through PR review.
