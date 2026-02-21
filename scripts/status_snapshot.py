#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT")
DEFAULT_MAX_LAG_HOURS = 48.0
DEFAULT_FLOOR = dt.datetime(2020, 1, 2, tzinfo=dt.timezone.utc)
BNB_FLOOR = dt.datetime(2020, 2, 15, tzinfo=dt.timezone.utc)


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _count_lines(path: Path) -> int:
    count = 0
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            count += chunk.count(b"\n")
    return count


def _read_first_nonempty_jsonl(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    return json.loads(line)
    except Exception:
        return None
    return None


def _read_last_nonempty_jsonl(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            if end == 0:
                return None
            cursor = end - 1
            buf = b""
            while cursor >= 0:
                f.seek(cursor)
                ch = f.read(1)
                if ch == b"\n":
                    if buf.strip():
                        break
                    buf = b""
                else:
                    buf = ch + buf
                cursor -= 1
            line = buf.decode("utf-8", errors="ignore").strip()
            if not line:
                return None
            return json.loads(line)
    except Exception:
        return None


def _parse_ts_utc(record: dict[str, Any] | None) -> dt.datetime | None:
    if not isinstance(record, dict):
        return None
    for key in ("ts", "open_time", "open_time_ms", "timestamp", "tt", "t"):
        if key not in record or record[key] is None:
            continue
        try:
            ts = int(record[key])
        except Exception:
            continue
        if ts > 10_000_000_000:
            return dt.datetime.fromtimestamp(ts / 1000, tz=dt.timezone.utc)
        return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
    return None


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _http_status(url: str, timeout: float = 1.5) -> int | None:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return int(getattr(res, "status", 200))
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception:
        return None


def _tcp_listen(host: str, port: int, timeout: float = 0.7) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    except Exception:
        return False
    finally:
        sock.close()


def _resolve_git_dir(repo_root: Path) -> Path | None:
    git_path = repo_root / ".git"
    if git_path.is_dir():
        return git_path
    if git_path.is_file():
        try:
            text = git_path.read_text(encoding="utf-8", errors="ignore").strip()
            if text.startswith("gitdir:"):
                rel = text.split("gitdir:", 1)[1].strip()
                return (repo_root / rel).resolve()
        except Exception:
            return None
    return None


def _resolve_head_sha(git_dir: Path) -> tuple[str | None, str | None]:
    head_path = git_dir / "HEAD"
    if not head_path.exists():
        return None, None
    try:
        head = head_path.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return None, None

    if head.startswith("ref: "):
        ref = head.split("ref: ", 1)[1].strip()
        branch = ref.split("/")[-1] if "/" in ref else ref
        ref_path = git_dir / ref
        if ref_path.exists():
            try:
                return branch, ref_path.read_text(encoding="utf-8").strip()[:12]
            except Exception:
                return branch, None
        packed = git_dir / "packed-refs"
        if packed.exists():
            try:
                for line in packed.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("^"):
                        continue
                    if " " not in line:
                        continue
                    sha, packed_ref = line.split(" ", 1)
                    if packed_ref == ref:
                        return branch, sha[:12]
            except Exception:
                return branch, None
        return branch, None

    return "detached", head[:12] if head else None


def _parse_gate_latest(path: Path, warnings: list[str]) -> dict[str, Any]:
    gate: dict[str, Any] = {
        "overall": "UNKNOWN",
        "timestamp_utc": None,
        "warn_count": None,
        "fail_count": None,
        "latest_pointer": str(path),
    }
    if not path.exists():
        warnings.append(f"gate file missing: {path}")
        return gate

    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if line.startswith("- Overall:"):
                gate["overall"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Timestamp (UTC):"):
                gate["timestamp_utc"] = line.split(":", 1)[1].strip()
            elif line.startswith("- WARN count:"):
                try:
                    gate["warn_count"] = int(line.split(":", 1)[1].strip())
                except Exception:
                    gate["warn_count"] = None
            elif line.startswith("- FAIL count:"):
                try:
                    gate["fail_count"] = int(line.split(":", 1)[1].strip())
                except Exception:
                    gate["fail_count"] = None
    except Exception as exc:
        warnings.append(f"gate parse failed: {exc}")
    return gate


def _collect_coverage(repo_root: Path, warnings: list[str]) -> dict[str, Any]:
    now = _utc_now()
    max_lag = dt.timedelta(hours=DEFAULT_MAX_LAG_HOURS)
    result: dict[str, Any] = {
        "overall_status": "PASS",
        "max_lag_hours": DEFAULT_MAX_LAG_HOURS,
        "symbols": {},
    }

    for symbol in DEFAULT_SYMBOLS:
        floor = BNB_FLOOR if symbol == "BNBUSDT" else DEFAULT_FLOOR
        path = repo_root / "data" / "derived" / symbol / "1m" / "klines.jsonl"
        payload = {
            "path": str(path),
            "rows": 0,
            "earliest_utc": None,
            "latest_utc": None,
            "lag_hours": None,
            "earliest_ok": False,
            "latest_ok": False,
            "status": "FAIL",
        }

        if not path.exists():
            warnings.append(f"coverage missing file: {path}")
            result["overall_status"] = "FAIL"
            result["symbols"][symbol] = payload
            continue

        first = _read_first_nonempty_jsonl(path)
        last = _read_last_nonempty_jsonl(path)
        if first is None or last is None:
            warnings.append(f"coverage empty/corrupt file: {path}")
            result["overall_status"] = "FAIL"
            result["symbols"][symbol] = payload
            continue

        earliest = _parse_ts_utc(first)
        latest = _parse_ts_utc(last)
        if earliest is None or latest is None:
            warnings.append(f"coverage timestamp parse failed: {path}")
            result["overall_status"] = "FAIL"
            result["symbols"][symbol] = payload
            continue

        rows = _count_lines(path)
        lag = now - latest
        earliest_ok = earliest <= floor
        latest_ok = lag <= max_lag
        status = "PASS" if earliest_ok and latest_ok else "FAIL"
        if status == "FAIL":
            result["overall_status"] = "FAIL"

        payload.update(
            {
                "rows": rows,
                "earliest_utc": _iso_utc(earliest),
                "latest_utc": _iso_utc(latest),
                "lag_hours": round(lag.total_seconds() / 3600, 2),
                "earliest_ok": earliest_ok,
                "latest_ok": latest_ok,
                "status": status,
            }
        )
        result["symbols"][symbol] = payload

    return result


def _collect_runs(repo_root: Path, warnings: list[str]) -> dict[str, Any]:
    root = repo_root / "data" / "backtests"
    runs: list[Path] = []
    if root.exists():
        for day_dir in root.iterdir():
            if not day_dir.is_dir():
                continue
            for run_dir in day_dir.iterdir():
                if run_dir.is_dir():
                    runs.append(run_dir)
    runs.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0.0, reverse=True)

    latest = runs[0] if runs else None
    latest_summary = {}
    required = (
        "summary.json",
        "equity_curve.jsonl",
        "gate.json",
        "regime_report.json",
        "optimizer.json",
        "optimizer_regime.json",
        "selection.json",
    )
    missing_artifacts: list[str] = []
    if latest is not None:
        summary_path = latest / "summary.json"
        summary = _read_json(summary_path)
        if isinstance(summary, dict):
            latest_summary = {
                "run_id": summary.get("run_id"),
                "timestamp": summary.get("timestamp"),
                "total_return": _to_float(summary.get("total_return")),
                "max_drawdown": _to_float(summary.get("max_drawdown")),
                "sharpe": _to_float(summary.get("sharpe")),
                "trades_count": summary.get("trades_count"),
                "win_rate": _to_float(summary.get("win_rate")),
            }
        else:
            warnings.append(f"latest summary missing/unreadable: {summary_path}")
        for name in required:
            if not (latest / name).exists():
                missing_artifacts.append(name)
    else:
        warnings.append("no backtest run directories found under data/backtests")

    return {
        "total": len(runs),
        "latest_run_dir": str(latest) if latest else None,
        "latest_run_id": latest.name if latest else None,
        "latest_summary": latest_summary,
        "latest_missing_artifacts": missing_artifacts,
        "newest_run_ids": [p.name for p in runs[:20]],
    }


def _collect_services(repo_root: Path) -> dict[str, Any]:
    ports = {}
    for port in (8501, 8502):
        listen = _tcp_listen("127.0.0.1", port)
        http_status = _http_status(f"http://127.0.0.1:{port}/", timeout=1.5) if listen else None
        ports[f"dashboard_{port}"] = {
            "listen": listen,
            "http_status": http_status,
            "http_200": http_status == 200,
        }

    home = Path.home()
    launch_labels = (
        "com.hongstr.dashboard",
        "com.hongstr.daily_etl",
        "com.hongstr.weekly_backfill",
        "com.hongstr.retention_cleanup",
    )
    launchd = {}
    for label in launch_labels:
        plist = home / "Library" / "LaunchAgents" / f"{label}.plist"
        launchd[label] = {"plist_present": plist.exists(), "plist_path": str(plist)}

    heartbeat = _read_json(repo_root / "data" / "state" / "services_heartbeat.json")
    return {"ports": ports, "launchd": launchd, "heartbeat": heartbeat if isinstance(heartbeat, dict) else {}}


def _collect_telemetry(warnings: list[str]) -> dict[str, Any]:
    dns_ok = True
    notes: list[str] = []
    try:
        socket.getaddrinfo("api.telegram.org", 443, type=socket.SOCK_STREAM)
    except Exception as exc:
        dns_ok = False
        msg = f"dns lookup failed for api.telegram.org: {type(exc).__name__}"
        notes.append(msg)
        warnings.append(msg)
    return {"dns_ok": dns_ok, "notes": notes}


def collect_status_snapshot(repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    root = root.resolve()
    warnings: list[str] = []

    git_dir = _resolve_git_dir(root)
    branch = None
    sha = None
    if git_dir is None:
        warnings.append(".git directory not found")
    else:
        branch, sha = _resolve_head_sha(git_dir)

    snapshot: dict[str, Any] = {
        "time_utc": _iso_utc(_utc_now()),
        "git": {"branch": branch, "sha": sha},
        "services": _collect_services(root),
        "coverage": _collect_coverage(root, warnings),
        "runs": _collect_runs(root, warnings),
        "gate": _parse_gate_latest(root / "reports" / "gate_latest.md", warnings),
        "telemetry": _collect_telemetry(warnings),
        "warnings": warnings,
    }
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit HONGSTR read-only status snapshot JSON")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    snapshot = collect_status_snapshot(args.repo_root)
    if args.pretty:
        print(json.dumps(snapshot, ensure_ascii=True, indent=2))
    else:
        print(json.dumps(snapshot, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
