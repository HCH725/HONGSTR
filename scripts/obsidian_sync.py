#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from obsidian_common import (
    DEFAULT_STATE_DIR,
    DEFAULT_STATE_FILE,
    DEFAULT_VAULT_ROOT,
    REPO_ROOT,
    build_daily_note_payload,
    build_incident_note_payloads,
    build_strategy_note_payloads,
    load_ssot_payloads,
    load_sync_state,
    now_utc_iso,
    save_sync_state,
    write_text_if_changed,
)


def sync_obsidian_notes(
    repo_root: Path = REPO_ROOT,
    now_utc: str | None = None,
    write_strategies: bool = True,
    write_incidents: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    state_dir = repo_root / DEFAULT_STATE_DIR.relative_to(REPO_ROOT)
    vault_root = repo_root / DEFAULT_VAULT_ROOT.relative_to(REPO_ROOT)
    state_path = repo_root / DEFAULT_STATE_FILE.relative_to(REPO_ROOT)
    effective_now = now_utc or now_utc_iso()

    payloads = load_ssot_payloads(state_dir)
    if not payloads:
        return {
            "changed": 0,
            "warnings": [f"WARN: no supported SSOT files found under {state_dir.as_posix()}"],
            "notes": [],
        }

    state = load_sync_state(state_path)
    planned_notes: list[dict[str, Any]] = []
    daily_note = build_daily_note_payload(payloads, effective_now)
    if daily_note:
        planned_notes.append(daily_note)
    if write_strategies:
        planned_notes.extend(build_strategy_note_payloads(payloads, state, effective_now))
    if write_incidents:
        planned_notes.extend(build_incident_note_payloads(payloads, effective_now))

    changed = 0
    note_summaries: list[str] = []
    for note in planned_notes:
        rel_path = note["vault_rel_path"]
        abs_path = vault_root / rel_path
        prior = state["notes"].get(rel_path, {})
        first_seen_utc = prior.get("first_seen_utc", note.get("first_seen_utc", effective_now))
        if write_text_if_changed(abs_path, note["content"], dry_run=dry_run):
            changed += 1
            action = "would_write" if dry_run else "wrote"
        else:
            action = "unchanged"
        note_summaries.append(f"{action}: {rel_path}")
        state["notes"][rel_path] = {
            "type": note["type"],
            "first_seen_utc": first_seen_utc,
            "last_synced_utc": effective_now,
            "source_hash": note["source_hash"],
            "content_hash": note["source_hash"],
        }

    save_sync_state(state_path, state, dry_run=dry_run)
    return {
        "changed": changed,
        "warnings": [],
        "notes": note_summaries,
        "state_path": state_path.as_posix(),
        "vault_root": vault_root.as_posix(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate human-readable Obsidian notes from SSOT state snapshots."
    )
    parser.add_argument("--now-utc", default=None, help="Override generated UTC timestamp.")
    parser.add_argument(
        "--write-strategies",
        choices=("on", "off"),
        default="on",
        help="Whether to write strategy cards.",
    )
    parser.add_argument(
        "--write-incidents",
        choices=("on", "off"),
        default="on",
        help="Whether to write incident cards.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute changes without writing notes or state.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = sync_obsidian_notes(
        now_utc=args.now_utc,
        write_strategies=args.write_strategies == "on",
        write_incidents=args.write_incidents == "on",
        dry_run=args.dry_run,
    )
    for warning in result.get("warnings", []):
        print(warning)
    for item in result.get("notes", []):
        print(item)
    if result.get("warnings") and not result.get("notes"):
        return 0
    print(
        f"obsidian_sync: changed={result.get('changed', 0)} "
        f"vault={result.get('vault_root', DEFAULT_VAULT_ROOT.as_posix())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
