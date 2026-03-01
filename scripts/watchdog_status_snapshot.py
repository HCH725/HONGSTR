#!/usr/bin/env python3
"""
Read-only watchdog status snapshot for SSOT.

Captures:
- `launchctl print gui/$UID/com.hongstr.tg_cp_watchdog`
- the last line from the watchdog stdout log

Writes:
- `reports/state_atomic/watchdog_status_latest.json`
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPO = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "watchdog_status.v1"
DEFAULT_LABEL = "com.hongstr.tg_cp_watchdog"
DEFAULT_LOG_PATH = Path.home() / "Library/Logs/hongstr/tg_cp_watchdog.out.log"
DEFAULT_OUTPUT_PATH = REPO / "reports/state_atomic/watchdog_status_latest.json"
TOP_LEVEL_KEYS = (
    "schema_version",
    "generated_utc",
    "ts_utc",
    "label",
    "launchctl_target",
    "status",
    "status_reason",
    "launchctl",
    "last_check",
    "sources",
)


def _utc_timestamp(ts: float | None) -> str:
    value = time.time() if ts is None else float(ts)
    return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_timestamp_opt(ts: float | None) -> str | None:
    if ts is None:
        return None
    return _utc_timestamp(ts)


def _as_int(value) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    token = text.split()[0]
    try:
        return int(float(token))
    except Exception:
        return None


def _parse_launchctl_output(stdout: str) -> dict:
    top_level: dict[str, str] = {}
    target = None
    depth = 0

    for idx, raw_line in enumerate(stdout.splitlines()):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if idx == 0:
            if " = " in stripped:
                target = stripped.split(" = ", 1)[0].strip()
            depth += stripped.count("{") - stripped.count("}")
            continue
        if depth == 1 and " = " in stripped:
            key, value = stripped.split(" = ", 1)
            top_level[key.strip()] = value.strip()
        depth += stripped.count("{") - stripped.count("}")

    return {
        "ok": bool(target),
        "target": target,
        "state": top_level.get("state"),
        "active_count": _as_int(top_level.get("active count")),
        "runs": _as_int(top_level.get("runs")),
        "last_exit_code": _as_int(top_level.get("last exit code")),
        "path": top_level.get("path"),
        "stdout_path": top_level.get("stdout path"),
        "stderr_path": top_level.get("stderr path"),
        "program": top_level.get("program"),
        "run_interval_seconds": _as_int(top_level.get("run interval")),
    }


def _read_last_line(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        tail = deque(handle, maxlen=1)
    if not tail:
        return ""
    return tail[0].rstrip("\r\n")


def _classify_log_line(line: str | None) -> tuple[str, str]:
    if line is None:
        return "UNKNOWN", "missing_log"
    text = str(line).strip()
    if not text:
        return "UNKNOWN", "empty_log"

    head, _, rest = text.partition(":")
    status = head.strip().upper()
    if status in {"PASS", "OK"}:
        return "OK", rest.strip() or text
    if status == "WARN":
        return "WARN", rest.strip() or text
    if status in {"FAIL", "ERROR"}:
        return "FAIL", rest.strip() or text
    return "UNKNOWN", text


def _inspect_log(path: Path, *, now_ts: float) -> dict:
    exists = path.exists()
    line = None
    updated_at_ts = None
    age_sec = None
    if exists:
        try:
            updated_at_ts = path.stat().st_mtime
            age_sec = max(0.0, now_ts - updated_at_ts)
        except Exception:
            updated_at_ts = None
            age_sec = None
        try:
            line = _read_last_line(path)
        except Exception as exc:
            line = f"read_error:{exc}"

    line_status, line_reason = _classify_log_line(line)
    return {
        "log_path": str(path),
        "exists": bool(exists),
        "last_line": line,
        "line_status": line_status,
        "line_reason": line_reason,
        "updated_at_utc": _utc_timestamp_opt(updated_at_ts),
        "age_sec": int(round(age_sec)) if age_sec is not None else None,
        "expected_within_sec": None,
    }


def _run_launchctl(
    target: str,
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> tuple[dict, int, str | None]:
    command = ["launchctl", "print", target]
    if runner is None:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    else:
        result = runner(command)

    stderr = (result.stderr or "").strip() or None
    if result.returncode != 0:
        meta = {
            "ok": False,
            "target": target,
            "state": None,
            "active_count": None,
            "runs": None,
            "last_exit_code": None,
            "path": None,
            "stdout_path": None,
            "stderr_path": None,
            "program": None,
            "run_interval_seconds": None,
        }
        return meta, int(result.returncode), stderr

    meta = _parse_launchctl_output(result.stdout or "")
    if not meta.get("target"):
        meta["target"] = target
    return meta, int(result.returncode), stderr


def _evaluate_watchdog_status(launchctl_meta: dict, last_check: dict) -> tuple[str, str]:
    if not bool(launchctl_meta.get("ok")):
        return "FAIL", "launchctl_unavailable"

    last_exit_code = launchctl_meta.get("last_exit_code")
    if last_exit_code not in (None, 0):
        return "FAIL", f"last_exit_code={last_exit_code}"

    runs = launchctl_meta.get("runs")
    if runs is None or runs <= 0:
        return "WARN", "watchdog_not_run_yet"

    interval = launchctl_meta.get("run_interval_seconds")
    if interval is not None:
        expected_within_sec = max(int(interval) * 3, 600)
        last_check["expected_within_sec"] = expected_within_sec
        age_sec = last_check.get("age_sec")
        if age_sec is not None and int(age_sec) > expected_within_sec:
            return "WARN", f"log_stale>{expected_within_sec}s"

    if not bool(last_check.get("exists")):
        return "WARN", "missing_watchdog_log"

    state = str(launchctl_meta.get("state") or "").strip().lower()
    active_count = launchctl_meta.get("active_count")
    if state == "running" or (active_count is not None and int(active_count) > 0):
        return "OK", "launchctl_running"
    if state == "not running":
        return "OK", "launchctl_idle_timer"
    if state:
        return "OK", f"launchctl_state={state}"
    return "OK", "launchctl_loaded"


def build_watchdog_snapshot(
    *,
    uid: int | None = None,
    label: str = DEFAULT_LABEL,
    log_path: Path = DEFAULT_LOG_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    now_ts: float | None = None,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> dict:
    current_ts = time.time() if now_ts is None else float(now_ts)
    target_uid = os.getuid() if uid is None else int(uid)
    launchctl_target = f"gui/{target_uid}/{label}"
    launchctl_meta, return_code, stderr = _run_launchctl(launchctl_target, runner=runner)
    last_check = _inspect_log(log_path, now_ts=current_ts)
    status, status_reason = _evaluate_watchdog_status(launchctl_meta, last_check)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": _utc_timestamp(current_ts),
        "ts_utc": _utc_timestamp(current_ts),
        "label": label,
        "launchctl_target": launchctl_target,
        "status": status,
        "status_reason": status_reason,
        "launchctl": {
            "ok": bool(launchctl_meta.get("ok")),
            "target": launchctl_meta.get("target") or launchctl_target,
            "state": launchctl_meta.get("state"),
            "active_count": launchctl_meta.get("active_count"),
            "runs": launchctl_meta.get("runs"),
            "last_exit_code": launchctl_meta.get("last_exit_code"),
            "path": launchctl_meta.get("path"),
            "stdout_path": launchctl_meta.get("stdout_path"),
            "stderr_path": launchctl_meta.get("stderr_path"),
            "program": launchctl_meta.get("program"),
            "run_interval_seconds": launchctl_meta.get("run_interval_seconds"),
            "command_return_code": return_code,
            "command_stderr": stderr,
        },
        "last_check": {
            "log_path": last_check.get("log_path"),
            "exists": bool(last_check.get("exists")),
            "last_line": last_check.get("last_line"),
            "line_status": last_check.get("line_status"),
            "line_reason": last_check.get("line_reason"),
            "updated_at_utc": last_check.get("updated_at_utc"),
            "age_sec": last_check.get("age_sec"),
            "expected_within_sec": last_check.get("expected_within_sec"),
        },
        "sources": {
            "launchctl_command": f"launchctl print {launchctl_target}",
            "log_path": str(log_path),
            "output_path": str(output_path),
        },
    }

    return {key: snapshot.get(key) for key in TOP_LEVEL_KEYS}


def write_snapshot(snapshot: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a read-only watchdog status snapshot.")
    parser.add_argument("--uid", type=int, default=os.getuid(), help="UID to use in launchctl target.")
    parser.add_argument("--label", default=DEFAULT_LABEL, help="launchd label to inspect.")
    parser.add_argument(
        "--log-path",
        default=str(DEFAULT_LOG_PATH),
        help="Path to the watchdog stdout log.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to write the atomic snapshot JSON.",
    )
    args = parser.parse_args()

    snapshot = build_watchdog_snapshot(
        uid=args.uid,
        label=args.label,
        log_path=Path(args.log_path),
        output_path=Path(args.output),
    )
    output_path = Path(args.output)
    write_snapshot(snapshot, output_path)
    print(f"Watchdog snapshot written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
