from __future__ import annotations

import argparse
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .allowlist import command_for_action, sanitize_action_requests
from .llm import NullLLM, build_llm_from_env
from .schema import AllowedAction, ControlPlaneDecision, ControlPlaneInputEvent, LLMStatus


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_json_blob(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise ValueError("Empty LLM output")

    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            return loaded
        raise ValueError("LLM output JSON must be an object")
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        fragment = text[start : end + 1]
        loaded = json.loads(fragment)
        if not isinstance(loaded, dict):
            raise ValueError("LLM output JSON fragment must be an object")
        return loaded


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    return [text] if text else []


def _sanitize_decision(
    raw: dict[str, Any],
    event_id: str,
    llm_mode: str,
) -> ControlPlaneDecision:
    notes = _as_str_list(raw.get("notes"))

    status_raw = str(raw.get("status", "WARN")).upper().strip()
    if status_raw not in {s.value for s in LLMStatus}:
        notes.append(f"Unknown status '{status_raw}' from LLM; coerced to WARN.")
        status_raw = LLMStatus.WARN.value

    allowed_actions_raw, rejected_actions = sanitize_action_requests(raw.get("actions", []))
    for rejected in rejected_actions:
        notes.append(f"Rejected non-allowlisted action: {rejected}")

    decision_data = {
        "schema_version": "1.0",
        "created_at_utc": _utc_now_iso(),
        "event_id": event_id,
        "llm_mode": llm_mode,
        "status": status_raw,
        "diagnosis": str(raw.get("diagnosis", "")).strip(),
        "summary": str(raw.get("summary", "")).strip(),
        "next_tasks": _as_str_list(raw.get("next_tasks")),
        "remediation_suggestions": _as_str_list(raw.get("remediation_suggestions")),
        "actions": allowed_actions_raw,
        "notes": notes,
    }

    return ControlPlaneDecision.model_validate(decision_data)


def _build_prompt(event: ControlPlaneInputEvent) -> str:
    event_json = json.dumps(event.model_dump(mode="json"), ensure_ascii=True)
    allowed = [a.value for a in AllowedAction]
    return (
        "Return strict JSON with fields: status, diagnosis, summary, next_tasks, "
        "remediation_suggestions, actions, notes. "
        "actions must be a list of objects {action, reason} and action must be one of: "
        f"{allowed}.\n"
        "Never output shell commands.\n"
        f"Input event:\n{event_json}"
    )


def _render_markdown(decision: ControlPlaneDecision) -> str:
    lines = [
        "# Control Plane Decision",
        "",
        f"- status: **{decision.status.value}**",
        f"- llm_mode: `{decision.llm_mode}`",
        f"- event_id: `{decision.event_id}`",
        f"- generated_at_utc: `{decision.created_at_utc.isoformat()}`",
        "",
        "## Diagnosis",
        decision.diagnosis or "(empty)",
        "",
        "## Summary",
        decision.summary or "(empty)",
        "",
        "## Next Tasks",
    ]
    if decision.next_tasks:
        lines.extend([f"- {item}" for item in decision.next_tasks])
    else:
        lines.append("- (none)")

    lines.extend(["", "## Safe Remediation Suggestions"])
    if decision.remediation_suggestions:
        lines.extend([f"- {item}" for item in decision.remediation_suggestions])
    else:
        lines.append("- (none)")

    lines.extend(["", "## Allowed Actions (Advisory Only)"])
    if decision.actions:
        for action in decision.actions:
            cmd = " ".join(command_for_action(action.action))
            reason = action.reason or "(no reason)"
            lines.append(f"- `{action.action.value}`: {reason}")
            lines.append(f"  - command: `{cmd}`")
    else:
        lines.append("- (none)")

    lines.extend(["", "## Notes"])
    if decision.notes:
        lines.extend([f"- {item}" for item in decision.notes])
    else:
        lines.append("- (none)")

    return "\n".join(lines) + "\n"


def _write_artifacts(
    decision: ControlPlaneDecision,
    output_json: Path,
    output_md: Path,
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(decision.model_dump(mode="json"), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(_render_markdown(decision), encoding="utf-8")


def run_control_plane(
    event_file: Path,
    output_json: Path,
    output_md: Path,
) -> int:
    fallback_decision = ControlPlaneDecision(
        status=LLMStatus.FAIL,
        diagnosis="Control-plane runner failure",
        summary="Unexpected failure before decision generation.",
        notes=[],
        llm_mode="null",
    )

    try:
        if not event_file.exists():
            fallback_decision.summary = f"Event file not found: {event_file}"
            _write_artifacts(fallback_decision, output_json, output_md)
            return 0

        try:
            event = ControlPlaneInputEvent.model_validate_json(
                event_file.read_text(encoding="utf-8")
            )
        except ValidationError as exc:
            fallback_decision.summary = "Event schema validation failed."
            fallback_decision.notes = [str(exc)]
            _write_artifacts(fallback_decision, output_json, output_md)
            return 0

        llm, llm_mode = build_llm_from_env()
        prompt = _build_prompt(event)
        llm_notes: list[str] = []

        try:
            raw_output = llm.generate(prompt)
        except Exception as exc:
            llm_notes.append(f"LLM call failed: {exc}")
            raw_output = NullLLM(reason="Primary LLM failed; fallback to NullLLM").generate(
                prompt
            )
            llm_mode = "null"

        try:
            raw_json = _extract_json_blob(raw_output)
            decision = _sanitize_decision(raw_json, event.event_id, llm_mode)
            if llm_notes:
                decision.notes.extend(llm_notes)
                if decision.status == LLMStatus.OK:
                    decision.status = LLMStatus.WARN
            _write_artifacts(decision, output_json, output_md)
            return 0
        except Exception as exc:
            fallback_decision.event_id = event.event_id
            fallback_decision.llm_mode = llm_mode
            fallback_decision.summary = "LLM output parsing/validation failed."
            fallback_decision.notes = llm_notes + [str(exc)]
            _write_artifacts(fallback_decision, output_json, output_md)
            return 0

    except Exception as exc:  # Never allow unhandled exception.
        fallback_decision.summary = f"Unhandled exception: {exc}"
        fallback_decision.notes = [traceback.format_exc()]
        _write_artifacts(fallback_decision, output_json, output_md)
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HONGSTR control-plane runner")
    parser.add_argument(
        "--event-file",
        default="data/events/latest_event.json",
        help="Path to router event JSON",
    )
    parser.add_argument(
        "--output-json",
        default="reports/control_plane_latest.json",
        help="Output decision JSON path",
    )
    parser.add_argument(
        "--output-md",
        default="reports/control_plane_latest.md",
        help="Output markdown summary path",
    )
    args = parser.parse_args(argv)

    return run_control_plane(
        event_file=Path(args.event_file),
        output_json=Path(args.output_json),
        output_md=Path(args.output_md),
    )


if __name__ == "__main__":
    raise SystemExit(main())
