#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any

import requests

try:
    import status_snapshot
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import status_snapshot

DEFAULT_RUNS_N = 10
MAX_RUNS_N = 50


def _warn(message: str) -> None:
    print(f"WARN: {message}")


def _load_env_file(repo_root: Path) -> None:
    env_file = repo_root / ".env"
    if not env_file.exists():
        return

    for raw in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]
        os.environ.setdefault(key, value)

    if not os.getenv("TG_BOT_TOKEN") and os.getenv("TELEGRAM_BOT_TOKEN"):
        os.environ["TG_BOT_TOKEN"] = os.environ["TELEGRAM_BOT_TOKEN"]
    if not os.getenv("TG_CHAT_ID") and os.getenv("TELEGRAM_CHAT_ID"):
        os.environ["TG_CHAT_ID"] = os.environ["TELEGRAM_CHAT_ID"]


def _fmt_pct(value: Any) -> str:
    try:
        if value is None:
            return "NA"
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return "NA"


def _fmt_num(value: Any, digits: int = 2) -> str:
    try:
        if value is None:
            return "NA"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "NA"


def _load_offset(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = int(payload.get("offset", 0))
        return value if value >= 0 else 0
    except Exception:
        return 0


def _save_offset(path: Path, offset: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"offset": int(offset), "updated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def parse_command(text: str) -> dict[str, Any] | None:
    stripped = (text or "").strip()
    if not stripped.startswith("/"):
        return None
    parts = stripped.split()
    head = parts[0].split("@", 1)[0].lower()
    args = parts[1:]

    if head == "/help":
        return {"name": "help"}
    if head == "/status":
        return {"name": "status"}
    if head == "/health":
        return {"name": "health"}
    if head == "/coverage":
        return {"name": "coverage"}
    if head == "/gate":
        return {"name": "gate"}
    if head == "/latest":
        return {"name": "latest"}
    if head == "/runs":
        n = DEFAULT_RUNS_N
        if args:
            try:
                n = int(args[0])
            except Exception:
                n = DEFAULT_RUNS_N
        if n < 1:
            n = 1
        if n > MAX_RUNS_N:
            n = MAX_RUNS_N
        return {"name": "runs", "n": n}
    return {"name": "unknown"}


def _render_help() -> str:
    return "\n".join(
        [
            "HONGSTR Telegram Text Dashboard (read-only)",
            "",
            "Commands:",
            "/help",
            "/status",
            "/health",
            "/coverage",
            "/gate",
            "/latest",
            "/runs [n]",
        ]
    )


def _render_status(snapshot: dict[str, Any]) -> str:
    git = snapshot.get("git", {})
    runs = snapshot.get("runs", {})
    latest = runs.get("latest_summary", {}) or {}
    coverage = snapshot.get("coverage", {})
    gate = snapshot.get("gate", {})
    ports = (snapshot.get("services", {}).get("ports", {}) or {})
    d8501 = ports.get("dashboard_8501", {})
    d8502 = ports.get("dashboard_8502", {})

    lines = [
        "HONGSTR Status",
        f"time_utc: {snapshot.get('time_utc', 'NA')}",
        f"git: {git.get('branch', 'NA')}@{git.get('sha', 'NA')}",
        f"dashboard 8501: listen={d8501.get('listen')} http_200={d8501.get('http_200')}",
        f"dashboard 8502: listen={d8502.get('listen')} http_200={d8502.get('http_200')}",
        f"coverage: {coverage.get('overall_status', 'UNKNOWN')}",
        f"gate: {gate.get('overall', 'UNKNOWN')} (warn={gate.get('warn_count')} fail={gate.get('fail_count')})",
        f"runs total: {runs.get('total', 0)} latest: {runs.get('latest_run_id') or 'NA'}",
        "latest metrics: "
        f"ret={_fmt_pct(latest.get('total_return'))} "
        f"mdd={_fmt_pct(latest.get('max_drawdown'))} "
        f"sharpe={_fmt_num(latest.get('sharpe'), 3)} "
        f"trades={latest.get('trades_count', 'NA')}",
    ]

    warnings = snapshot.get("warnings", []) or []
    if warnings:
        lines.append(f"warnings: {len(warnings)} (showing first)")
        lines.append(f"- {warnings[0]}")
    return "\n".join(lines)


def _render_health(snapshot: dict[str, Any]) -> str:
    services = snapshot.get("services", {}) or {}
    ports = services.get("ports", {}) or {}
    launchd = services.get("launchd", {}) or {}
    heartbeat = services.get("heartbeat", {}) or {}

    lines = ["Health"]
    for port_name in ("dashboard_8501", "dashboard_8502"):
        p = ports.get(port_name, {})
        lines.append(
            f"{port_name}: listen={p.get('listen')} http_status={p.get('http_status')} http_200={p.get('http_200')}"
        )
    lines.append("launchd plist presence:")
    for label in (
        "com.hongstr.dashboard",
        "com.hongstr.daily_etl",
        "com.hongstr.weekly_backfill",
        "com.hongstr.retention_cleanup",
    ):
        item = launchd.get(label, {})
        lines.append(f"- {label}: plist_present={item.get('plist_present')}")

    if heartbeat:
        updated = heartbeat.get("updated_at_utc")
        lines.append(f"heartbeat updated_at_utc: {updated}")
        services_list = heartbeat.get("services", [])
        for svc in services_list[:5]:
            name = svc.get("name", "unknown")
            status = svc.get("status", "unknown")
            lines.append(f"- heartbeat {name}: {status}")
    else:
        lines.append("heartbeat: unavailable")
    return "\n".join(lines)


def _render_coverage(snapshot: dict[str, Any]) -> str:
    coverage = snapshot.get("coverage", {}) or {}
    symbols = coverage.get("symbols", {}) or {}
    lines = [
        "Coverage (1m)",
        f"overall: {coverage.get('overall_status', 'UNKNOWN')} max_lag_hours={coverage.get('max_lag_hours', 'NA')}",
        "symbol | rows | earliest_utc | latest_utc | lag_h | status",
    ]
    for symbol in DEFAULT_SYMBOLS:
        item = symbols.get(symbol, {})
        lines.append(
            f"{symbol} | {item.get('rows', 0)} | {item.get('earliest_utc') or 'NA'} | "
            f"{item.get('latest_utc') or 'NA'} | {item.get('lag_hours') if item.get('lag_hours') is not None else 'NA'} | "
            f"{item.get('status', 'FAIL')}"
        )
    return "\n".join(lines)


def _render_gate(snapshot: dict[str, Any]) -> str:
    gate = snapshot.get("gate", {}) or {}
    lines = [
        "Gate",
        f"overall: {gate.get('overall', 'UNKNOWN')}",
        f"timestamp_utc: {gate.get('timestamp_utc') or 'NA'}",
        f"warn_count: {gate.get('warn_count')}",
        f"fail_count: {gate.get('fail_count')}",
        f"source: {gate.get('latest_pointer')}",
    ]
    return "\n".join(lines)


def _render_latest(snapshot: dict[str, Any]) -> str:
    runs = snapshot.get("runs", {}) or {}
    latest = runs.get("latest_summary", {}) or {}
    lines = [
        "Latest Backtest",
        f"run_id: {runs.get('latest_run_id') or 'NA'}",
        f"run_dir: {runs.get('latest_run_dir') or 'NA'}",
        f"timestamp: {latest.get('timestamp') or 'NA'}",
        f"ret: {_fmt_pct(latest.get('total_return'))}",
        f"mdd: {_fmt_pct(latest.get('max_drawdown'))}",
        f"sharpe: {_fmt_num(latest.get('sharpe'), 3)}",
        f"trades: {latest.get('trades_count', 'NA')}",
        f"win_rate: {_fmt_pct(latest.get('win_rate'))}",
    ]
    missing = runs.get("latest_missing_artifacts", []) or []
    if missing:
        lines.append("missing artifacts:")
        lines.extend([f"- {name}" for name in missing[:10]])
    else:
        lines.append("missing artifacts: none")
    return "\n".join(lines)


def _render_runs(snapshot: dict[str, Any], n: int) -> str:
    runs = snapshot.get("runs", {}) or {}
    ids = (runs.get("newest_run_ids", []) or [])[:n]
    lines = [
        "Runs",
        f"total: {runs.get('total', 0)}",
        f"showing newest: {len(ids)}",
    ]
    for idx, run_id in enumerate(ids, start=1):
        lines.append(f"{idx}. {run_id}")
    return "\n".join(lines)


class TelegramClient:
    def __init__(
        self,
        token: str,
        retries: int,
        backoff: int,
        connect_timeout: int,
        request_timeout: int,
    ) -> None:
        self.token = token
        self.retries = max(1, retries)
        self.backoff = max(1, backoff)
        self.connect_timeout = max(1, connect_timeout)
        self.request_timeout = max(1, request_timeout)
        self.base = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()

    def _request(self, endpoint: str, payload: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
        url = f"{self.base}/{endpoint}"
        attempt = 1
        while attempt <= self.retries:
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=(self.connect_timeout, self.request_timeout),
                )
                status_code = response.status_code
                data: dict[str, Any] = {}
                try:
                    data = response.json()
                except Exception:
                    data = {}

                if status_code >= 500:
                    reason = f"http_{status_code}"
                    if attempt < self.retries:
                        _warn(f"{endpoint} attempt {attempt}/{self.retries} failed ({reason}); retrying")
                        time.sleep(self.backoff * (2 ** (attempt - 1)))
                        attempt += 1
                        continue
                    _warn(f"{endpoint} failed after {attempt} attempts ({reason})")
                    return False, data

                if status_code >= 400:
                    desc = data.get("description", f"http_{status_code}")
                    _warn(f"{endpoint} non-retryable client error: {desc}")
                    return False, data

                if data.get("ok") is True:
                    return True, data
                desc = data.get("description", "unknown_response")
                _warn(f"{endpoint} api error: {desc}")
                return False, data
            except requests.Timeout:
                reason = "timeout"
            except requests.ConnectionError as exc:
                msg = str(exc)
                if "resolve host" in msg.lower() or "name resolution" in msg.lower():
                    reason = "dns"
                else:
                    reason = "connection"
            except Exception as exc:
                reason = type(exc).__name__

            if attempt < self.retries:
                _warn(f"{endpoint} attempt {attempt}/{self.retries} failed ({reason}); retrying")
                time.sleep(self.backoff * (2 ** (attempt - 1)))
                attempt += 1
                continue

            _warn(f"{endpoint} failed after {attempt} attempts ({reason})")
            return False, None
        return False, None

    def get_updates(self, offset: int, timeout: int) -> list[dict[str, Any]]:
        ok, data = self._request(
            "getUpdates",
            {"offset": offset, "timeout": timeout, "allowed_updates": ["message"]},
        )
        if not ok or not isinstance(data, dict):
            return []
        updates = data.get("result", [])
        if isinstance(updates, list):
            return [u for u in updates if isinstance(u, dict)]
        return []

    def send_message(self, chat_id: str, text: str) -> bool:
        trimmed = text[:3900]
        ok, _ = self._request("sendMessage", {"chat_id": chat_id, "text": trimmed})
        return ok


def _render_for_command(command: dict[str, Any], snapshot: dict[str, Any] | None) -> str:
    name = command.get("name")
    if name == "help":
        return _render_help()
    if snapshot is None:
        return "WARN: snapshot unavailable"
    if name == "status":
        return _render_status(snapshot)
    if name == "health":
        return _render_health(snapshot)
    if name == "coverage":
        return _render_coverage(snapshot)
    if name == "gate":
        return _render_gate(snapshot)
    if name == "latest":
        return _render_latest(snapshot)
    if name == "runs":
        return _render_runs(snapshot, int(command.get("n", DEFAULT_RUNS_N)))
    return "Unknown command. Use /help"


def _chat_is_allowed(chat_id: str, configured_chat_id: str) -> bool:
    if not configured_chat_id:
        return True
    return str(chat_id) == str(configured_chat_id)


def run_once(
    repo_root: Path,
    client: TelegramClient,
    configured_chat_id: str,
    offset_path: Path,
    poll_timeout: int,
) -> int:
    offset = _load_offset(offset_path)
    updates = client.get_updates(offset=offset, timeout=poll_timeout)
    if not updates:
        return 0

    next_offset = offset
    snapshot_cache: dict[str, Any] | None = None
    for update in updates:
        update_id = int(update.get("update_id", 0))
        next_offset = max(next_offset, update_id + 1)

        message = update.get("message", {})
        if not isinstance(message, dict):
            continue
        text = message.get("text")
        if not isinstance(text, str):
            continue
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        if not chat_id or not _chat_is_allowed(chat_id, configured_chat_id):
            continue

        command = parse_command(text)
        if command is None:
            continue
        if command.get("name") != "help":
            snapshot_cache = status_snapshot.collect_status_snapshot(repo_root)
        response = _render_for_command(command, snapshot_cache)
        client.send_message(chat_id, response)

    _save_offset(offset_path, next_offset)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="HONGSTR Telegram read-only text dashboard")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    parser.add_argument("--poll-timeout", type=int, default=25, help="Telegram long-poll timeout seconds")
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[1]
    repo_root = repo_root.resolve()
    _load_env_file(repo_root)

    token = os.getenv("TG_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TG_CHAT_ID", "").strip()
    if not token:
        _warn("TG_BOT_TOKEN missing; Telegram text dashboard disabled")
        return 0

    retries = int(os.getenv("TG_RETRIES", "3"))
    backoff = int(os.getenv("TG_RETRY_BACKOFF_SEC", "2"))
    connect_timeout = int(os.getenv("TG_CONNECT_TIMEOUT", "5"))
    timeout = int(os.getenv("TG_TIMEOUT", "8"))
    client = TelegramClient(
        token=token,
        retries=retries,
        backoff=backoff,
        connect_timeout=connect_timeout,
        request_timeout=timeout,
    )

    offset_path = repo_root / "data" / "state" / "tg_offset.json"
    if args.once:
        return run_once(repo_root, client, chat_id, offset_path, max(1, args.poll_timeout))

    while True:
        run_once(repo_root, client, chat_id, offset_path, max(1, args.poll_timeout))
        time.sleep(1.0)


if __name__ == "__main__":
    raise SystemExit(main())
