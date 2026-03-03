#!/usr/bin/env python3
"""
HONGSTR Research Trigger Queue
Minimal helpers for the poller to check/drain pending events.

Usage (from poller):
    from research.loop.trigger_queue import peek_pending, mark_drained
"""
import json
from pathlib import Path
from typing import List, Dict, Any

DEFAULT_QUEUE_PATH = Path(__file__).resolve().parent.parent.parent / "data/state/_research/trigger_queue.jsonl"
DRAIN_MARKER_SUFFIX = ".drained_offset"


def _drain_marker(queue_path: Path) -> Path:
    return queue_path.parent / (queue_path.name + DRAIN_MARKER_SUFFIX)


def read_all(queue_path: Path = DEFAULT_QUEUE_PATH) -> List[Dict[str, Any]]:
    """Read all events from trigger_queue.jsonl. Returns [] if file missing."""
    queue_path = Path(queue_path)
    if not queue_path.exists():
        return []
    events = []
    for line in queue_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def peek_pending(queue_path: Path = DEFAULT_QUEUE_PATH) -> bool:
    """
    Return True if there are unprocessed (pending) events in the queue.
    Strategy: compare current line count against the drained offset.
    A queue is pending if it has more lines than the last known drained offset.
    """
    queue_path = Path(queue_path)
    if not queue_path.exists():
        return False

    lines = [l for l in queue_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    total = len(lines)
    if total == 0:
        return False

    marker = _drain_marker(queue_path)
    if marker.exists():
        try:
            drained = int(marker.read_text().strip())
            return total > drained
        except (ValueError, OSError):
            pass

    # No marker → any non-empty queue is considered pending
    return True


def mark_drained(queue_path: Path = DEFAULT_QUEUE_PATH):
    """Record how many lines have been processed (current line count)."""
    queue_path = Path(queue_path)
    if not queue_path.exists():
        return
    lines = [l for l in queue_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    marker = _drain_marker(queue_path)
    marker.write_text(str(len(lines)))


def enqueue(event: Dict[str, Any], queue_path: Path = DEFAULT_QUEUE_PATH):
    """
    Append a trigger event to the queue with de-duplication (idempotency).
    Default window: 3600s (1 hour).
    """
    try:
        queue_path = Path(queue_path)
        queue_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate idempotency key if missing
        if "key" not in event:
            import datetime
            import os
            dedupe_sec = int(os.environ.get("HONGSTR_RESEARCH_TRIGGER_DEDUPE_SEC", "3600"))
            ts_epoch = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            bucket = ts_epoch // dedupe_sec
            trigger = event.get("trigger", "unknown")
            event["key"] = f"{trigger}:{bucket}"

        new_key = event["key"]

        # Check for duplicates in last 200 lines
        if queue_path.exists():
            try:
                # Read last 20k bytes (~200 lines) for efficiency
                with open(queue_path, "rb") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    if size > 0:
                        f.seek(max(0, size - 20000), 0)
                        last_lines = f.read().decode("utf-8", "ignore").splitlines()
                        for line in reversed(last_lines):
                            if not line.strip():
                                continue
                            try:
                                old_evt = json.loads(line)
                                if old_evt.get("key") == new_key:
                                    # Duplicate found, skip enqueue
                                    return
                            except json.JSONDecodeError:
                                continue
            except Exception:
                pass # Stability-first: if read fails, just append

        with open(queue_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass # Stability-first: never crash the caller
