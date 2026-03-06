#!/usr/bin/env python3
"""
Manual helper to emit non-canonical atomic alert artifacts.

This script is intentionally narrow:
- writes only under reports/state_atomic/*
- does not touch data/state/*
- is not wired into refresh_state, tg_cp, or central steward runtime
- may derive a single alert from watchdog_status_latest.json when present
- otherwise emits a stable sample artifact for schema validation
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UTC = timezone.utc
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT
DEFAULT_WATCHDOG_INPUT = Path("reports/state_atomic/watchdog_status_latest.json")
DEFAULT_ALERTS_LATEST = Path("reports/state_atomic/alerts_latest.json")
DEFAULT_ALERTS_JOURNAL = Path("reports/state_atomic/alerts_journal.jsonl")


def utc_now_iso() -> str:
    return (
        datetime.now(tz=UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def write_atomic_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    lines = [
        json.dumps(record, ensure_ascii=False, sort_keys=False)
        for record in records
    ]
    tmp_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    tmp_path.replace(path)


def read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text == "PASS":
        text = "OK"
    if text not in {"OK", "WARN", "FAIL", "UNKNOWN"}:
        return "UNKNOWN"
    return text


def slugify(text: str, *, fallback: str) -> str:
    out = []
    for ch in str(text or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {" ", "-", "_", ":", "/", "."}:
            out.append("_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or fallback


def routing_for_status(status: str) -> tuple[str, str, str]:
    if status == "OK":
        return ("record_for_summary", "none", "record_only")
    return ("send_telegram_alert", "telegram_central_steward", "telegram_notify")


def severity_for_status(status: str) -> str:
    if status == "OK":
        return "INFO"
    if status == "WARN":
        return "WARN"
    return "ERROR"


def build_sample_alert(now_utc: str) -> dict[str, Any]:
    return {
        "event_id": "aev1_sample_atomic_alert",
        "ts_utc": now_utc,
        "source": "scripts/state_atomic/emit_atomic_alert_artifacts.py",
        "owner_plane": "control_plane",
        "severity": "WARN",
        "alert_type": "sample_atomic_alert",
        "summary": "Sample atomic alert artifact for schema validation only; not canonical SSOT.",
        "evidence_paths": [
            "scripts/state_atomic/emit_atomic_alert_artifacts.py",
            "docs/architecture/alert_artifact_skeleton_v1.md",
        ],
        "ssot_paths": [
            "reports/state_atomic/alerts_latest.json",
            "reports/state_atomic/alerts_journal.jsonl",
        ],
        "next_action": "record_for_summary",
        "dedupe_key": "sample_atomic_alert:control_plane",
        "cooldown_key": "sample_atomic_alert:control_plane",
        "recovery_of": None,
        "escalation_target": "none",
        "repair_class": "record_only",
    }


def build_watchdog_alert(snapshot: dict[str, Any], *, watchdog_input_rel: str, now_utc: str) -> dict[str, Any]:
    status = normalize_status(snapshot.get("status"))
    status_reason = str(
        snapshot.get("status_reason")
        or (snapshot.get("last_check") or {}).get("line_reason")
        or "watchdog_status_observed"
    ).strip()
    status_slug = slugify(status_reason, fallback="watchdog_status_observed")
    next_action, escalation_target, repair_class = routing_for_status(status)

    if status == "OK":
        summary = "Watchdog snapshot is OK; atomic alert artifact remains non-canonical and read-only."
    elif status == "WARN":
        summary = "Watchdog snapshot is WARN; review canonical watchdog mirror before operator notification."
    else:
        summary = "Watchdog snapshot is non-OK; steward may summarize this artifact but may not recompute system health."

    ts_utc = str(snapshot.get("ts_utc") or snapshot.get("generated_utc") or now_utc).strip() or now_utc

    return {
        "event_id": f"aev1_watchdog_{status.lower()}_{status_slug}",
        "ts_utc": ts_utc,
        "source": "scripts/watchdog_status_snapshot.py",
        "owner_plane": "control_plane",
        "severity": severity_for_status(status),
        "alert_type": "watchdog_health",
        "summary": summary,
        "evidence_paths": [
            "scripts/watchdog_status_snapshot.py",
            watchdog_input_rel,
        ],
        "ssot_paths": [
            watchdog_input_rel,
            "data/state/watchdog_status_latest.json",
        ],
        "next_action": next_action,
        "dedupe_key": f"watchdog_health:{status.lower()}:{status_slug}",
        "cooldown_key": "watchdog_health:control_plane",
        "recovery_of": None,
        "escalation_target": escalation_target,
        "repair_class": repair_class,
    }


def build_latest_payload(alert: dict[str, Any], *, now_utc: str) -> dict[str, Any]:
    return {
        "schema_version": "alerts_latest.v1",
        "generated_utc": now_utc,
        "source": "scripts/state_atomic/emit_atomic_alert_artifacts.py",
        "owner_plane": str(alert.get("owner_plane") or "control_plane"),
        "alerts": [alert],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit atomic alert artifacts under reports/state_atomic/*.")
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory under which reports/state_atomic/* will be written.",
    )
    parser.add_argument(
        "--watchdog-input",
        default=str(DEFAULT_WATCHDOG_INPUT),
        help="Watchdog atomic input path, absolute or relative to output-root.",
    )
    parser.add_argument(
        "--latest-output",
        default=str(DEFAULT_ALERTS_LATEST),
        help="alerts_latest.json path, absolute or relative to output-root.",
    )
    parser.add_argument(
        "--journal-output",
        default=str(DEFAULT_ALERTS_JOURNAL),
        help="alerts_journal.jsonl path, absolute or relative to output-root.",
    )
    parser.add_argument(
        "--sample-only",
        action="store_true",
        help="Ignore watchdog input and emit a stable sample artifact.",
    )
    return parser.parse_args()


def resolve_path(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root).resolve()
    watchdog_input = resolve_path(output_root, args.watchdog_input)
    latest_output = resolve_path(output_root, args.latest_output)
    journal_output = resolve_path(output_root, args.journal_output)
    now_utc = utc_now_iso()

    alert: dict[str, Any]
    mode: str
    if args.sample_only:
        alert = build_sample_alert(now_utc)
        mode = "sample"
    else:
        watchdog_payload = read_json(watchdog_input)
        if isinstance(watchdog_payload, dict) and watchdog_payload:
            rel_input = (
                watchdog_input.relative_to(output_root).as_posix()
                if watchdog_input.is_relative_to(output_root)
                else str(watchdog_input)
            )
            alert = build_watchdog_alert(watchdog_payload, watchdog_input_rel=rel_input, now_utc=now_utc)
            mode = "watchdog"
        else:
            alert = build_sample_alert(now_utc)
            mode = "sample_fallback"

    latest_payload = build_latest_payload(alert, now_utc=now_utc)
    write_atomic_json(latest_output, latest_payload)
    write_atomic_jsonl(journal_output, [alert])

    print(f"mode={mode}")
    print(f"alerts_latest={latest_output}")
    print(f"alerts_journal={journal_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
