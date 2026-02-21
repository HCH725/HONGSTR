#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_FILES = [
    "logs/launchd_daily_etl.out.log",
    "logs/launchd_daily_etl.err.log",
    "logs/launchd_weekly_backfill.out.log",
    "logs/launchd_weekly_backfill.err.log",
    "logs/launchd_daily_backtest.out.log",
    "logs/launchd_daily_backtest.err.log",
]

SECRET_PATTERNS = [
    (re.compile(r"(?i)(TG_BOT_TOKEN\s*[=:]\s*)([^\s,;]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(TG_CHAT_ID\s*[=:]\s*)([^\s,;]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)([A-Z0-9_]*(?:KEY|SECRET|TOKEN)\s*[=:]\s*)([^\s,;]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(https?://[^\s]*[?&](?:token|key|secret)=)([^&\s]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(/bot)([0-9]{6,}:[A-Za-z0-9_\-]{20,})"), r"\1***REDACTED***"),
]


def redact_text(text: str) -> str:
    redacted = text
    for pattern, repl in SECRET_PATTERNS:
        redacted = pattern.sub(repl, redacted)
    return redacted


def redact_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: redact_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_obj(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def tail_text(path: Path, lines: int) -> str:
    if not path.exists():
        return f"MISSING: {path}"

    try:
        proc = subprocess.run(
            ["tail", "-n", str(lines), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        output = proc.stdout if proc.stdout else proc.stderr
        return redact_text(output.strip())
    except Exception as exc:
        return f"ERROR tailing {path}: {exc}"


def run_script(repo_root: Path, script_rel: str, skip: bool) -> dict[str, Any]:
    command = ["/bin/bash", script_rel]
    if skip:
        return {
            "command": command,
            "return_code": 0,
            "output": "SKIPPED (--skip-commands)",
        }

    try:
        proc = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return {
            "command": command,
            "return_code": proc.returncode,
            "output": redact_text(combined.strip()),
        }
    except Exception as exc:
        return {
            "command": command,
            "return_code": 1,
            "output": f"ERROR running {script_rel}: {exc}",
        }


def build_event(repo_root: Path, tail_lines: int, skip_commands: bool) -> dict[str, Any]:
    gate_report = tail_text(repo_root / "reports/gate_latest.md", tail_lines)
    coverage = run_script(repo_root, "scripts/check_data_coverage.sh", skip_commands)
    health = run_script(repo_root, "scripts/healthcheck_dashboard.sh", skip_commands)

    log_tails: dict[str, str] = {}
    for rel in DEFAULT_LOG_FILES:
        log_tails[rel] = tail_text(repo_root / rel, tail_lines)

    latest_backtest_out = sorted((repo_root / "logs").glob("daily_backtest_*.out.log"))
    latest_backtest_err = sorted((repo_root / "logs").glob("daily_backtest_*.err.log"))
    if latest_backtest_out:
        rel = latest_backtest_out[-1].relative_to(repo_root).as_posix()
        log_tails[rel] = tail_text(latest_backtest_out[-1], tail_lines)
    if latest_backtest_err:
        rel = latest_backtest_err[-1].relative_to(repo_root).as_posix()
        log_tails[rel] = tail_text(latest_backtest_err[-1], tail_lines)

    event = {
        "schema_version": "1.0",
        "event_id": f"evt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "event_router",
        "payload": {
            "gate_report_excerpt": gate_report,
            "coverage_check": coverage,
            "dashboard_healthcheck": health,
            "log_tails": log_tails,
            "context": {
                "repo_root": str(repo_root),
                "tail_lines": tail_lines,
                "skip_commands": skip_commands,
            },
        },
    }
    return redact_obj(event)


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit control-plane input event JSON")
    parser.add_argument("--output", default="data/events/latest_event.json")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--tail-lines", type=int, default=120)
    parser.add_argument("--skip-commands", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path

    event = build_event(
        repo_root=repo_root,
        tail_lines=max(args.tail_lines, 10),
        skip_commands=args.skip_commands,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(event, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
