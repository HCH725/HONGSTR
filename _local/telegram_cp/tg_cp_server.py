#!/usr/bin/env python3
"""HONGSTR 中樞管家 — LLM-first Telegram control-plane.

Architecture:
  • Every free-text message → Qwen (Ollama /api/chat) with system prompt,
    conversation history, and live system snapshot.
  • /commands (start, help, status …) → deterministic quick-path, no LLM.
  • Hard guardrail: guardrail.py checks BEFORE and AFTER LLM reply.
  • Strictly read-only — no shell, no writes, no restarts, no trades.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("tg_cp_server")

# Ensure project root is in sys.path for _local imports
REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from _local.telegram_cp.args_schema import parse_args, validate  # type: ignore
except Exception:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from args_schema import parse_args, validate  # type: ignore

try:
    from _local.telegram_cp.guardrail import is_action_request, refusal_message, redact_secrets  # type: ignore
except Exception:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from guardrail import is_action_request, refusal_message, redact_secrets  # type: ignore

try:
    from _local.telegram_cp.router import should_use_specialist
    from _local.telegram_cp.reasoning_client import call_reasoning_specialist
except Exception:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from router import should_use_specialist
    from reasoning_client import call_reasoning_specialist

# ────────────────────── paths ──────────────────────
REPO = Path(os.environ.get("HONGSTR_REPO", "/Users/hong/Projects/HONGSTR"))
LOCAL_DIR = REPO / "_local/telegram_cp"
STATE_DIR = REPO / "data/state/_tg_cp"
OFFSET_PATH = STATE_DIR / "offset.json"
SESSION_PATH = STATE_DIR / "session_state.json"
OPS_MEM = STATE_DIR / "ops_memory.jsonl"
USER_MEM = STATE_DIR / "user_memory.jsonl"
RUNTIME_LOG = STATE_DIR / "runtime.log"
ALERTS_PENDING = STATE_DIR / "alerts_pending.jsonl"  # written by notify_telegram.sh / scripts
FOLLOWUP_QUEUE = STATE_DIR / "followup_queue.jsonl"

POLICY_PATH = LOCAL_DIR / "policy.json"
PERSONA_PATH = LOCAL_DIR / "persona.md"
SKILLS_PATH = LOCAL_DIR / "skills_registry.json"
REFUSAL_PATH = LOCAL_DIR / "refusal_templates.md"
SAFE_SOP_PATH = LOCAL_DIR / "safe_sop_snippets.md"

# ────────────────────── env ──────────────────────
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
TG_BOT_USERNAME = os.environ.get("TG_BOT_USERNAME", "").lstrip("@")

OLLAMA_ENDPOINT = os.environ.get("HONGSTR_LLM_ENDPOINT", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("HONGSTR_LLM_MODEL", "qwen2.5:7b-instruct")
OLLAMA_TEMPERATURE = float(os.environ.get("HONGSTR_LLM_TEMPERATURE", "0.45"))
MAX_REPLY_CHARS = int(os.environ.get("HONGSTR_TG_MAX_REPLY_CHARS", "1800"))
HISTORY_MAX_TURNS = int(os.environ.get("HONGSTR_TG_HISTORY_TURNS", "10"))

# Daily briefing schedule (local time)
BRIEFING_HOUR = int(os.environ.get("HONGSTR_BRIEFING_HOUR", "8"))
BRIEFING_MINUTE = int(os.environ.get("HONGSTR_BRIEFING_MINUTE", "30"))
BRIEFING_ENABLED = os.environ.get("HONGSTR_BRIEFING_ENABLED", "1") != "0"

# Deferred followup config
FOLLOWUP_MAX_DELAY_MIN = int(os.environ.get("HONGSTR_FOLLOWUP_MAX_MIN", "60"))
FOLLOWUP_ENABLED = os.environ.get("HONGSTR_FOLLOWUP_ENABLED", "1") != "0"

# ────────────────────── basic io ──────────────────────
def _safe_enqueue(trigger: str, source: str = "tg_cp", details: dict = None):
    """Safely enqueue a research trigger without blocking or failing the main path."""
    try:
        from research.loop.trigger_queue import enqueue
        from datetime import datetime, timezone
        evt = {
            "ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": source,
            "trigger": trigger,
            "details": details or {}
        }
        enqueue(evt)
        logger.info(f"Trigger enqueued: {trigger} from {source}")
    except Exception as e:
        logger.warning(f"Failed to enqueue trigger {trigger}: {e}")


def _load_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return default


def _load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def _save_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _append_jsonl(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _ensure_state() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    for p in [OPS_MEM, USER_MEM, RUNTIME_LOG]:
        if not p.exists():
            p.write_text("", encoding="utf-8")


def log_event(event: str, **kwargs: object) -> None:
    _ensure_state()
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    parts = [f"ts={ts}", f"event={event}"]
    for k, v in kwargs.items():
        s = str(v).replace("\n", " ")
        if len(s) > 220:
            s = s[:220] + "..."
        parts.append(f"{k}={s}")
    line = " ".join(parts)
    print(line, flush=True)
    try:
        with RUNTIME_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


# ────────────────────── config ──────────────────────
POLICY = _load_json(POLICY_PATH, {})
PERSONA = _load_text(PERSONA_PATH, "")
SKILLS = _load_json(SKILLS_PATH, {"skills": []}).get("skills", [])
SKILL_MAP = {s.get("name"): s for s in SKILLS if isinstance(s, dict)}
REFUSAL_TXT = _load_text(REFUSAL_PATH, "")
SAFE_SOP_TXT = _load_text(SAFE_SOP_PATH, "")
MAX_QUESTIONS = 1


def _allowed_chats() -> set[int]:
    out = set()
    for part in (TG_CHAT_ID or "").split(","):
        p = part.strip()
        if not p:
            continue
        try:
            out.add(int(p))
        except Exception:
            continue
    return out


ALLOWED_CHATS = _allowed_chats()

# ────────────────────── telegram api ──────────────────────
def _tg_api(method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))
    except Exception as exc:
        log_event("TG_API_ERR", method=method, err=type(exc).__name__)
        return {"ok": False, "description": str(exc)}


def _get_updates(offset: int) -> dict:
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/getUpdates?timeout=25&limit=50&offset={offset}"
    try:
        with urllib.request.urlopen(url, timeout=35) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "ignore")[:200]
        except Exception:
            pass
        log_event("UPDATES_ERR", err=f"HTTP{exc.code}", detail=body)
        return {"ok": False, "result": [], "_http_error": exc.code}
    except Exception as exc:
        log_event("UPDATES_ERR", err=type(exc).__name__)
        return {"ok": False, "result": []}


def _clean_reply(text: str) -> str:
    """Apply post-processing: redact secrets, limit questions, trim length."""
    cleaned = redact_secrets((text or "").strip())
    # strip rigid headings that LLM sometimes generates
    blocked = ("先講結論", "現況", "影響", "下一步", "唯讀上下文")
    lines = []
    for line in cleaned.splitlines():
        if any(k in line for k in blocked):
            continue
        lines.append(line.rstrip())
    cleaned = "\n".join(lines).strip()
    # normalize whitespace
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    # limit question marks
    if MAX_QUESTIONS > 0:
        count = 0
        out = []
        for ch in cleaned:
            if ch in ("?", "？"):
                count += 1
                if count > MAX_QUESTIONS:
                    continue
            out.append(ch)
        cleaned = "".join(out)
    if not cleaned:
        cleaned = "（空回覆，請再試一次）"
    if len(cleaned) > MAX_REPLY_CHARS:
        cleaned = cleaned[: MAX_REPLY_CHARS - 16] + "\n...(truncated)"
    return cleaned


def _send(chat_id: int, text: str, reply_to: int | None = None) -> bool:
    cleaned = _clean_reply(text)
    payload: dict = {"chat_id": chat_id, "text": cleaned, "disable_web_page_preview": True}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    res = _tg_api("sendMessage", payload)
    ok = bool(res.get("ok"))
    log_event("REPLY", chat_id=chat_id, ok=1 if ok else 0)
    return ok


# ────────────────────── state ──────────────────────
def _load_offset() -> int:
    return int(_load_json(OFFSET_PATH, {"offset": 0}).get("offset", 0))


def _save_offset(offset: int) -> None:
    _save_json(OFFSET_PATH, {"offset": int(offset)})


def _load_session_state() -> dict:
    data = _load_json(SESSION_PATH, {"chats": {}})
    if not isinstance(data, dict):
        return {"chats": {}}
    data.setdefault("chats", {})
    return data


def _save_session_state(state: dict) -> None:
    _save_json(SESSION_PATH, state)


def _chat_key(chat_id: int) -> str:
    return str(int(chat_id))


# ────────────────────── conversation history ──────────────────────
def _get_history(state: dict, chat_id: int) -> list[dict]:
    """Return list of {role, content} from session state."""
    key = _chat_key(chat_id)
    chats = state.setdefault("chats", {})
    chat_state = chats.setdefault(key, {})
    history = chat_state.get("history")
    if not isinstance(history, list):
        return []
    return history


def _append_history(state: dict, chat_id: int, role: str, content: str) -> None:
    """Append a message and trim to HISTORY_MAX_TURNS * 2."""
    key = _chat_key(chat_id)
    chats = state.setdefault("chats", {})
    chat_state = chats.setdefault(key, {})
    history = chat_state.setdefault("history", [])
    if not isinstance(history, list):
        history = []
        chat_state["history"] = history
    history.append({"role": role, "content": content})
    max_msgs = HISTORY_MAX_TURNS * 2
    if len(history) > max_msgs:
        chat_state["history"] = history[-max_msgs:]


# ────────────────────── helpers ──────────────────────
def _tail(path: Path, n: int = 60) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]
    except Exception:
        return []


def _file_age_hours(path: Path) -> float | None:
    try:
        return max(0.0, (time.time() - path.stat().st_mtime) / 3600.0)
    except Exception:
        return None


def _evaluate_freshness(age_hours: float | None) -> tuple[str, str | None]:
    """Return (status, reason) where status is OK, WARN, or FAIL."""
    if age_hours is None:
        return "WARN", "missing file"
    if age_hours <= 12.0:
        return "OK", None
    if age_hours <= 48.0:
        return "WARN", f"exceeds 12h ({age_hours:.1f}h)"
    return "FAIL", f"exceeds 48h ({age_hours:.1f}h)"


def _strip_mention(text: str) -> str:
    out = (text or "").strip()
    if TG_BOT_USERNAME:
        out = re.sub(rf"@{re.escape(TG_BOT_USERNAME)}", "", out, flags=re.IGNORECASE)
    return out.strip()


def _cmd_base(text: str) -> str:
    raw = (text or "").strip()
    token = raw.split()[0].strip() if raw else ""
    if not token.startswith("/"):
        return ""
    # Normalize Telegram command suffix:
    # "/status@HONGSTR_bot" -> "/status"
    token = token.split("@", 1)[0].strip()
    return token.lower()


def _status_ssot_sources() -> list[tuple[str, Path]]:
    return [
        ("freshness_table.json", REPO / "data/state/freshness_table.json"),
        ("coverage_matrix_latest.json", REPO / "data/state/coverage_matrix_latest.json"),
        ("brake_health_latest.json", REPO / "data/state/brake_health_latest.json"),
        ("regime_monitor_latest.json", REPO / "data/state/regime_monitor_latest.json"),
    ]


def _status_ssot_sources_line() -> str:
    names = [name for name, _ in _status_ssot_sources()]
    return "Sources: " + ", ".join(names)


def _status_rank(status: str) -> int:
    s = (status or "").upper()
    if s in {"FAIL", "ERROR"}:
        return 2
    if s in {"WARN", "NEEDS_REBASE", "UNKNOWN"}:
        return 1
    return 0


def _status_max(*statuses: str) -> str:
    best = "OK"
    best_rank = -1
    for s in statuses:
        r = _status_rank(s)
        if r > best_rank:
            best_rank = r
            best = s.upper() if s else "OK"
    if best not in {"OK", "WARN", "FAIL", "UNKNOWN", "NEEDS_REBASE"}:
        return "UNKNOWN"
    if best == "NEEDS_REBASE":
        return "WARN"
    return best


def _fmt_num(v: float | int | None) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.1f}"
    except Exception:
        return "N/A"


def _read_coverage_table_rebase(path: Path) -> tuple[int | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return None, "unreadable"

    latest_by_key: dict[str, dict] = {}
    for ln in lines:
        if not ln.strip():
            continue
        try:
            row = json.loads(ln)
        except Exception:
            return None, "unreadable"
        if not isinstance(row, dict):
            return None, "unreadable"
        key_obj = row.get("coverage_key")
        if isinstance(key_obj, dict):
            key = json.dumps(key_obj, ensure_ascii=False, sort_keys=True)
        else:
            key = str(key_obj)
        latest_by_key[key] = row

    rebase = 0
    for row in latest_by_key.values():
        if str(row.get("status", "")).upper() == "NEEDS_REBASE":
            rebase += 1
    return rebase, None


def _status_short_report() -> str:
    parsed: dict[str, object] = {}
    missing: list[str] = []
    unreadable: list[str] = []

    source_map = {name: path for name, path in _status_ssot_sources()}
    for name, path in source_map.items():
        if name.endswith(".jsonl"):
            continue
        if not path.exists():
            missing.append(name)
            continue
        try:
            data = _load_json(path, {})
            if not isinstance(data, dict) or not data:
                unreadable.append(name)
                continue
            parsed[name] = data
        except Exception:
            unreadable.append(name)

    rebase_count = 0

    freshness_rows = (parsed.get("freshness_table.json") or {}).get("rows", []) if isinstance(parsed.get("freshness_table.json"), dict) else []
    cov_rows = (parsed.get("coverage_matrix_latest.json") or {}).get("rows", []) if isinstance(parsed.get("coverage_matrix_latest.json"), dict) else []
    cov_totals = (parsed.get("coverage_matrix_latest.json") or {}).get("totals", {}) if isinstance(parsed.get("coverage_matrix_latest.json"), dict) else {}
    brake_results = (parsed.get("brake_health_latest.json") or {}).get("results", []) if isinstance(parsed.get("brake_health_latest.json"), dict) else []
    regime = parsed.get("regime_monitor_latest.json") if isinstance(parsed.get("regime_monitor_latest.json"), dict) else {}

    if not isinstance(freshness_rows, list):
        unreadable.append("freshness_table.json")
        freshness_rows = []
    if not isinstance(cov_rows, list):
        unreadable.append("coverage_matrix_latest.json")
        cov_rows = []
    if not isinstance(cov_totals, dict):
        cov_totals = {}
    if not isinstance(brake_results, list):
        unreadable.append("brake_health_latest.json")
        brake_results = []
    if not isinstance(regime, dict):
        unreadable.append("regime_monitor_latest.json")
        regime = {}

    if missing or unreadable:
        miss = ", ".join(sorted(set(missing))) if missing else "none"
        bad = ", ".join(sorted(set(unreadable))) if unreadable else "none"
        return "\n".join(
            [
                "SSOT_STATUS: WARN",
                f"Issues: missing=[{miss}] unreadable=[{bad}]",
                "Freshness: N/A",
                "CoverageMatrix: N/A",
                "Brake: N/A",
                "Regime: N/A",
                _status_ssot_sources_line(),
            ]
        )

    fresh_statuses = [str(r.get("status", "UNKNOWN")).upper() for r in freshness_rows if isinstance(r, dict)]
    fresh_status = "OK"
    if fresh_statuses:
        fresh_status = _status_max(*fresh_statuses)
    max_age = None
    for r in freshness_rows:
        if not isinstance(r, dict):
            continue
        age = r.get("age_h")
        try:
            age_v = float(age)
        except Exception:
            continue
        max_age = age_v if max_age is None else max(max_age, age_v)

    matrix_rebase = int(cov_totals.get("rebase", 0) or 0)
    max_lag = None
    cov_status_raw = [str(r.get("status", "UNKNOWN")).upper() for r in cov_rows if isinstance(r, dict)]
    done_count = cov_totals.get("done")
    blocked_count = cov_totals.get("blocked", 0)
    total_count = None
    if "done" in cov_totals and "inProgress" in cov_totals and "blocked" in cov_totals:
        total_count = cov_totals["done"] + cov_totals["inProgress"] + cov_totals["blocked"]
    else:
        total_count = len(cov_rows)
        done_count = sum(1 for s in cov_status_raw if s == "PASS")

    for r in cov_rows:
        if not isinstance(r, dict):
            continue
        lag = r.get("lag_hours")
        try:
            lag_v = float(lag)
        except Exception:
            continue
        max_lag = lag_v if max_lag is None else max(max_lag, lag_v)

    max_lag_val = max_lag if max_lag is not None else 0.0
    if total_count == 0:
        cov_status = "UNKNOWN"
    elif blocked_count > 0 or max_lag_val > 48:
        cov_status = "FAIL"
    elif max_lag_val > 12:
        cov_status = "WARN"
    else:
        cov_status = "PASS"

    brake_overall_fail = bool((parsed.get("brake_health_latest.json") or {}).get("overall_fail")) if isinstance(parsed.get("brake_health_latest.json"), dict) else False
    brake_status = "FAIL" if brake_overall_fail else "OK"
    for r in brake_results:
        if not isinstance(r, dict):
            continue
        brake_status = _status_max(brake_status, str(r.get("status", "UNKNOWN")))

    regime_status = str(regime.get("overall", "UNKNOWN")).upper()
    if regime_status not in {"OK", "WARN", "FAIL"}:
        regime_status = "UNKNOWN"

    rebase_status = "WARN" if matrix_rebase > 0 else "OK"
    overall = _status_max(fresh_status, cov_status, brake_status, regime_status, rebase_status)

    return "\n".join(
        [
            f"SSOT_STATUS: {overall}",
            f"Freshness: {fresh_status} max_age_h={_fmt_num(max_age)}",
            f"CoverageMatrix: {cov_status} {done_count}/{total_count} done | max_lag_h={_fmt_num(max_lag)} | rebase={matrix_rebase}",
            f"Brake: {brake_status}",
            f"Regime: {regime_status}",
            _status_ssot_sources_line(),
        ]
    )


def _chat_allowed(msg: dict) -> bool:
    chat = msg.get("chat") or {}
    chat_id = int(chat.get("id", 0) or 0)
    if chat_id not in ALLOWED_CHATS:
        return False

    text = (msg.get("text") or "").strip()
    if text.startswith("/"):
        return True

    if not POLICY.get("group_gating", {}).get("require_mention_or_reply", True):
        return True

    ctype = (chat.get("type") or "").lower()
    if ctype == "private":
        return True

    reply_to = msg.get("reply_to_message") or {}
    rb = reply_to.get("from") or {}
    if rb.get("is_bot") and (not TG_BOT_USERNAME or rb.get("username", "") == TG_BOT_USERNAME):
        return True

    if TG_BOT_USERNAME and f"@{TG_BOT_USERNAME}".lower() in text.lower():
        return True
    return False


# ────────────────────── system snapshot (read-only) ──────────────────────
def _collect_snapshot() -> dict:
    """Read all available read-only signals from logs, reports, and alerts."""
    dashboard_log = REPO / "logs/launchd_dashboard.out.log"
    etl_log = REPO / "logs/launchd_daily_etl.out.log"
    weekly_log = REPO / "logs/launchd_weekly_backfill.out.log"
    healthcheck_log = REPO / "logs/launchd_daily_healthcheck.out.log"
    backtest_log = REPO / "logs/launchd_daily_backtest.out.log"
    realtime_log = REPO / "logs/launchd_realtime_ws.out.log"

    # dashboard health
    dash_tail = "\n".join(_tail(dashboard_log, 50))
    dash_ok = any(k in dash_tail for k in ["HTTP/1.1 200", "HTTP 200", "dashboard healthy"])

    # data freshness
    freshness = {}
    freshness_snap = _load_json(REPO / "data/state/freshness_table.json", {})
    if freshness_snap and "rows" in freshness_snap:
        # Prioritize unified snapshot
        for row in freshness_snap["rows"]:
            sym = row.get("symbol")
            tf = row.get("tf")
            if sym not in freshness: freshness[sym] = {}
            freshness[sym][tf] = {
                "age_hours": row.get("age_h"),
                "status": row.get("status", "FAIL"),
                "reason": row.get("reason")
            }
    else:
        # Fallback to manual scan if snapshot missing
        for sym in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
            freshness[sym] = {}
            for tf in ["1m", "1h", "4h"]:
                p = REPO / f"data/derived/{sym}/{tf}/klines.jsonl"
                age = _file_age_hours(p)
                status, reason = _evaluate_freshness(age)
                freshness[sym][tf] = {"age_hours": age, "status": status, "reason": reason}

    # Log freshness evaluation
    max_age = 0.0
    offenders = []
    for sym, tfs in freshness.items():
        for tf, d in tfs.items():
            age = d["age_hours"] or 0.0
            max_age = max(max_age, age)
            if d["status"] != "OK":
                offenders.append(f"{sym}_{tf}")
    
    log_event("FRESHNESS_EVAL", max_age=round(max_age, 1), offenders_n=len(offenders), offenders=",".join(offenders))

    # control plane report
    cp = _load_json(REPO / "reports/control_plane_latest.json", {})
    cp_status = cp.get("status", "UNKNOWN")
    cp_summary = (cp.get("summary") or "").strip()[:300]
    cp_age = _file_age_hours(REPO / "reports/control_plane_latest.json")

    # action items report
    ai = _load_json(REPO / "reports/action_items_latest.json", {})
    overall_gate = ai.get("overall_gate", "UNKNOWN")
    top_action = ""
    tops = ai.get("top_actions") or []
    if tops and isinstance(tops[0], dict):
        top_action = tops[0].get("title", "")

    # launchd log ages (tells us when jobs last ran)
    log_ages = {
        "etl": _file_age_hours(etl_log),
        "healthcheck": _file_age_hours(healthcheck_log),
        "backtest": _file_age_hours(backtest_log),
        "weekly_backfill": _file_age_hours(weekly_log),
        "realtime_ws": _file_age_hours(realtime_log),
    }

    # etl recent status (look for OK/FAIL in last 10 lines)
    etl_tail = "\n".join(_tail(etl_log, 10))
    etl_ok = "ETL OK" in etl_tail or "Complete" in etl_tail
    etl_fail = "ETL FAIL" in etl_tail or "ERROR" in etl_tail

    # regime monitor
    regime = _load_json(REPO / "data/state/regime_monitor_latest.json", {})

    # brake health
    brake_health = _load_json(REPO / "data/state/brake_health_latest.json", {})

    # coverage / rebase summary
    rebase_count = 0
    total_coverage = 0
    cov_lag_max = 0.0
    cov_found = False
    cov_done = 0
    cov_blocked = 0
    
    matrix = _load_json(REPO / "data/state/coverage_matrix_latest.json", {})
    if matrix and "rows" in matrix:
        cov_found = True
        cov_totals = matrix.get("totals", {})
        rebase_count = cov_totals.get("rebase", 0)
        
        if "done" in cov_totals and "inProgress" in cov_totals and "blocked" in cov_totals:
            total_coverage = cov_totals.get("done", 0) + cov_totals.get("inProgress", 0) + cov_totals.get("blocked", 0)
            cov_done = cov_totals.get("done", 0)
            cov_blocked = cov_totals.get("blocked", 0)
        else:
            total_coverage = len(matrix["rows"])
            cov_done = sum(1 for r in matrix["rows"] if str(r.get("status", "")).upper() == "PASS")
            cov_blocked = sum(1 for r in matrix["rows"] if str(r.get("status", "")).upper() == "FAIL")
        
        for row in matrix["rows"]:
            lag = row.get("lag_hours")
            if lag is not None and lag > cov_lag_max:
                cov_lag_max = lag

    pending_alerts = _count_pending_alerts()

    return {
        "dashboard_ok": dash_ok,
        "freshness": freshness,
        "cp_status": cp_status,
        "cp_summary": cp_summary,
        "cp_age_hours": cp_age,
        "overall_gate": overall_gate,
        "top_action": top_action,
        "log_ages": log_ages,
        "etl_ok": etl_ok,
        "etl_fail": etl_fail,
        "regime_monitor": regime,
        "pending_alerts": pending_alerts,
        "brake_health": brake_health,
        "rebase_count": rebase_count,
        "total_coverage": total_coverage,
        "cov_lag_max": cov_lag_max,
        "cov_found": cov_found,
        "cov_done": cov_done,
        "cov_blocked": cov_blocked,
    }


def _snapshot_text() -> str:
    """Build a compact text summary of system state for LLM system prompt."""
    snap = _collect_snapshot()
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    parts = [f"[系統快照 {now}]"]

    # dashboard
    parts.append(f"Dashboard: {'正常運行' if snap['dashboard_ok'] else '可能有問題'}")

    # data freshness
    fresh_lines = []
    overall_ok = True
    any_fail = False
    
    for sym in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
        sym_data = snap["freshness"].get(sym, {})
        tf_results = []
        for tf in ["1m", "1h", "4h"]:
            d = sym_data.get(tf, {})
            age = d.get("age_hours")
            status = d.get("status", "WARN")
            if status != "OK": overall_ok = False
            if status == "FAIL": any_fail = True
            
            age_str = f"{age:.1f}h" if age is not None else "缺失"
            tf_results.append(f"{tf}:{age_str}({status})")
        
        fresh_lines.append(f"{sym}: {' / '.join(tf_results)}")

    if overall_ok:
        parts.append("資料新鮮度: ✅ 良好 (皆在 12h 內)")
    elif any_fail:
        parts.append("資料新鮮度: ❌ 嚴重落後 (部分超過 48h)")
    else:
        parts.append("資料新鮮度: ⚠️ 延遲 (部分超過 12h)")
    
    parts.extend(fresh_lines)

    # etl status
    if snap["etl_fail"]:
        parts.append("ETL: 最近執行有 FAIL")
    elif snap["etl_ok"]:
        parts.append("ETL: 最近執行正常")
    else:
        etl_age = snap["log_ages"].get("etl")
        parts.append(f"ETL: log 約 {etl_age:.0f}h 前" if etl_age is not None else "ETL: log 不存在")

    # control plane
    cp_age = snap["cp_age_hours"]
    parts.append(f"ControlPlane 報告: status={snap['cp_status']}, 約 {cp_age:.0f}h 前" if cp_age is not None else f"ControlPlane: status={snap['cp_status']}")
    if snap["cp_summary"]:
        parts.append(f"CP 摘要: {snap['cp_summary']}")

    # backtest gate
    parts.append(f"Backtest Gate: {snap['overall_gate']}")
    if snap["top_action"]:
        parts.append(f"優先行動: {snap['top_action']}")

    # pending alerts
    if snap["pending_alerts"] > 0:
        parts.append(f"⚠️ 待處理排程告警: {snap['pending_alerts']} 筆")

    return "\n".join(parts)


# ────────────────────── skills (read-only) ──────────────────────
def skill_status_overview(include_sources: bool = False) -> str:
    snap = _collect_snapshot()
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    lines = [f"目前快照時間：{now}"]
    lines.append("• Dashboard: {}".format("穩定" if snap["dashboard_ok"] else "有波動"))
    
    # Calculate worst case freshness
    max_age = 0.0
    worst_sym = "?"
    worst_tf = "?"
    worst_status = "OK"
    
    for sym, tfs in snap["freshness"].items():
        for tf, d in tfs.items():
            age = d.get("age_hours") or 0.0
            if age > max_age:
                max_age = age
                worst_sym = sym
                worst_tf = tf
                worst_status = d.get("status", "OK")
    
    status_emoji = "✅" if worst_status == "OK" else ("⚠️" if worst_status == "WARN" else "❌")
    thresh_info = "<=12h" if worst_status == "OK" else (">12h, <=48h" if worst_status == "WARN" else ">48h")
    lines.append(f"• Freshness: {status_emoji} {worst_status} (max_age={max_age:.1f}h {thresh_info}, {worst_sym} {worst_tf})")
    
    # Brake summary (R3-D+)
    brake = snap.get("brake_health", {})
    if not brake:
        lines.append("• Brake: NOT FOUND (run ./.venv/bin/python scripts/brake_healthcheck.py)")
    else:
        results = brake.get("results", [])
        any_fail = brake.get("overall_fail", False)
        any_warn = any(r.get("status") == "WARN" for r in results)
        
        status = "FAIL" if any_fail else ("WARN" if any_warn else "OK")
        icon = "❌" if status == "FAIL" else ("⚠️" if status == "WARN" else "✅")
        
        # Build concise reason
        issues = [f"{r['item']} {r['status']}" for r in results if r.get("status") in ["WARN", "FAIL"]]
        reason = ", ".join(issues) if issues else "All OK"
        lines.append(f"• Brake: {icon} {status} - {reason}")
    
    # Coverage / Rebase Summary
    if not snap.get("cov_found"):
        lines.append("• CoverageMatrix: UNKNOWN (run coverage snapshot/refresh_state)")
    else:
        cnt = snap.get("rebase_count", 0)
        max_lag = snap.get("cov_lag_max", 0.0)
        cov_done = snap.get("cov_done", 0)
        total_cov = snap.get("total_coverage", 0)
        cov_blocked = snap.get("cov_blocked", 0)

        if total_cov == 0:
            status = "UNKNOWN"
        elif cov_blocked > 0 or max_lag > 48:
            status = "FAIL"
        elif max_lag > 12:
            status = "WARN"
        else:
            status = "PASS"

        lines.append(f"• CoverageMatrix: {status} {cov_done}/{total_cov} done | max_lag_h={max_lag:.1f} | rebase={cnt}")

    if include_sources:
        lines.append("\n來源快照: freshness_table.json, coverage_matrix_latest.json")
    return "\n".join(lines)


def skill_freshness_detail() -> str:
    snap = _collect_snapshot()
    lines = ["📊 資料新鮮度完整報表 (BTC/ETH/BNB × 1m/1h/4h)"]
    
    any_stale = False
    any_fail = False
    for sym in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
        sym_data = snap["freshness"].get(sym, {})
        tf_results = []
        for tf in ["1m", "1h", "4h"]:
            d = sym_data.get(tf, {})
            age = d.get("age_hours")
            status = d.get("status", "WARN")
            if status != "OK": any_stale = True
            if status == "FAIL": any_fail = True
            age_str = f"{age:.1f}h" if age is not None else "缺失"
            tf_results.append(f"{tf}: {age_str} ({status})")
        lines.append(f"• {sym}: {' | '.join(tf_results)}")
    
    if any_stale:
        lines.append("\n⚠️ 自修引導:")
        lines.append("• 這是資料延遲，不代表交易有問題，請保持冷靜。")
        lines.append("• 建議執行: `bash scripts/check_data_coverage.sh` 查看缺口。")
        lines.append("• 請檢查 `logs/launchd_daily_etl.out.log` 確認 ETL 狀態。")
        if any_fail:
            lines.append("• 🔴 偵測到嚴重落後 (>48h)，建議優先人工介入追資料。")
            _safe_enqueue(trigger="freshness_fail", details={"any_fail": True})
        elif any_stale:
            _safe_enqueue(trigger="freshness_warn", details={"any_stale": True})

    lines.append("\n💡 備註：此回報僅供參考資料完整性，不影響下單邏輯。系統目前為唯讀監控模式，不會主動發起交易或修改任何設定。")
    return "\n".join(lines)


def skill_ml_status() -> str:
    evidence_p = REPO / "reports/research/ml/evidence_summary.json"
    signal_p = REPO / "reports/research/signals/signal_1h_24.parquet"
    
    results = []
    ok_count = 0
    
    # 1. evidence summary
    if evidence_p.exists():
        age = _file_age_hours(evidence_p)
        age_str = f"{age:.1f}h 前更新" if age is not None else "存在"
        results.append(f"• Evidence Summary: ✅ {age_str}")
        ok_count += 1
    else:
        results.append("• Evidence Summary: ❌ 缺失")
        
    # 2. signal parquet
    if signal_p.exists():
        try:
            import pandas as pd
            row_count = len(pd.read_parquet(signal_p))
            if row_count > 0:
                results.append(f"• ML Signals: ✅ 存在 ({row_count} rows)")
                ok_count += 1
            else:
                results.append("• ML Signals: ⚠️ 檔案存在但無資料 (rowcount=0)")
        except Exception as e:
            results.append(f"• ML Signals: ⚠️ 讀取失敗 ({type(e).__name__})")
    else:
        results.append("• ML Signals: ❌ 缺失 (signal_1h_24.parquet)")
        
    status_header = "✅ ML Pipeline 正常" if ok_count == 2 else "⚠️ ML Pipeline 異常"
    lines = [f"🤖 {status_header}", ""]
    lines.extend(results)
    
    if ok_count < 2:
        _safe_enqueue(trigger="ml_fail", details={"ok_count": ok_count})
        lines.append("\n💡 處置建議:")
        lines.append("• 請先確認『資料新鮮度』是否正常。")
        lines.append("• 資料正常後，可嘗試手動執行: `bash scripts/ml_daily_manual.sh` (僅提示，請手動執行)。")
    
    return "\n".join(lines)


def skill_research_status() -> str:
    """Read-only: show today's research loop state and leaderboard top entry."""
    STATE_PATH = REPO / "data/state/_research/loop_state.json"
    LEADERBOARD_PATH = REPO / "data/state/_research/leaderboard.json"
    state = _load_json(STATE_PATH, {})

    if not state:
        return (
            "🔬 **Research Loop 狀態**\n"
            "• 尚未執行過 (loop_state.json 不存在)\n"
            "• 手動觸發: `bash scripts/run_research_loop.sh --once`"
        )

    last_run_raw = state.get("last_run", "")
    status = state.get("status", "UNKNOWN")
    last_exp = state.get("last_exp") or "N/A"
    gate_passed = state.get("gate_passed")
    report_path = state.get("report_path") or "N/A"
    error = state.get("error")
    actions = state.get("actions", [])

    from datetime import datetime as _dt, timezone as _tz
    today_str = _dt.now(_tz.utc).strftime("%Y-%m-%d")
    ran_today = last_run_raw.startswith(today_str)

    gate_icon = "✅" if gate_passed else ("❌" if gate_passed is False else "❓")
    lines = [
        f"🔬 **Research Loop 狀態** ({status})",
        f"• 今日是否執行: {'✅ 已執行' if ran_today else '⏳ 尚未執行 (排程 06:20 或手動觸發)'}",
        f"• 上次執行: {last_run_raw[:19] if last_run_raw else 'N/A'}",
        f"• 實驗 ID: {last_exp}",
        f"• Gate: {gate_icon} {'PASSED' if gate_passed else ('FAILED' if gate_passed is False else 'N/A')}",
        f"• 報告: `{report_path.split('/')[-1] if report_path != 'N/A' else 'N/A'}`",
        f"• actions: {actions} (report_only, 安全)",
    ]

    if status == "WARN" and error:
        lines.append(f"\n⚠️ **WARN 原因**: {error[:200]}")
        lines.append("💡 回退: `git checkout origin/main -- research/loop/`")

    leaderboard = _load_json(LEADERBOARD_PATH, [])
    if leaderboard and isinstance(leaderboard, list):
        top = leaderboard[0]
        lines.append(f"\n🏆 **Leaderboard Top**: {top.get('experiment_id','?')} | OOS Sharpe={top.get('oos_sharpe',0):.2f}")

    if not ran_today:
        lines.append("\n💡 手動觸發: `bash scripts/run_research_loop.sh --once`")

    return "\n".join(lines)


def skill_regime_status() -> str:
    snap = _collect_snapshot()
    data = snap.get("regime_monitor", {})
    status = data.get("overall", "UNKNOWN")
    ts_utc = data.get("ts_utc", "UNKNOWN")
    
    # Check for data gaps in freshness
    any_stale = False
    for sym, tfs in snap["freshness"].items():
        for tf, d in tfs.items():
            if d.get("status") != "OK":
                any_stale = True
    
    lines = [f"🌐 市場機制監控 (Regime Monitor): {status}"]
    lines.append(f"• 更新時間: {ts_utc}")
    
    if status == "UNKNOWN":
        lines.append("❌ 尚未產生快照。")
        lines.append("💡 建議執行: `.venv/bin/python scripts/phase4_regime_monitor.py` 重新產生。")
        return "\n".join(lines)

    current = data.get("current", {})
    sharpe = current.get("sharpe", 0)
    mdd = current.get("mdd", 0)
    trades = current.get("trades", 0)
    summary_src = current.get("summary_path") or "N/A"
    src_reason = current.get("source_reason") or "state_missing"
    
    lines.append(f"• Sharpe: {sharpe:.3f} | MDD: {mdd:.2%} | Trades: {trades}")
    lines.append(f"• 來源: `{summary_src}` ({src_reason})")
    
    if summary_src == "N/A":
        lines.append("⚠️ 診斷資料不全，請執行: `bash scripts/refresh_state.sh` 後重啟監控。")
    
    # Conclusion
    reasons = data.get("reason", [])
    reason_str = reasons[0] if reasons else "正常運行中"
    lines.append(f"\n結論: {status} — {reason_str}")
    if status in ["WARN", "FAIL"]:
        trigger = f"regime_{status.lower()}"
        _safe_enqueue(trigger=trigger, details={"status": status, "ts": ts_utc})
    
    # Proof-by-contradiction
    lines.append("\n反證：排除資料缺口")
    if not any_stale:
        lines.append("✅ 資料新鮮度良好 (BTC/ETH/BNB 皆在 12h 內)")
        lines.append("✅ 資料缺口可能性低 (Data gap unlikely cause)")
        lines.append("💡 驗證指令: `bash scripts/check_data_coverage.sh` (應顯示 PASS)")
    else:
        lines.append("⚠️ 偵測到資料過時 (Partially STALE/FAIL)")
        lines.append("🔴 需優先排除缺口，資料不全可能導致判定偏誤")
        lines.append("💡 建議執行: `bash scripts/refresh_state.sh` 後檢查 ETL 日誌")

    # SOP
    lines.append("\n下一步檢查順序:")
    if any_stale:
        lines.append("1. 執行 `bash scripts/check_data_coverage.sh` 確認缺口")
        lines.append("2. 檢查 `logs/launchd_daily_etl.out.log` 排除 ETL 錯誤")
        lines.append("3. 執行 `bash scripts/refresh_state.sh` 強制重整")
    
    idx = 4 if any_stale else 1
    lines.append(f"{idx}. 查看 regime 源文件: `cat {summary_src}`")
    lines.append(f"{idx+1}. 手動重跑診斷: `PYTHONPATH=. .venv/bin/python scripts/phase4_regime_monitor.py`")
    lines.append(f"{idx+2}. 檢查判定細節: `grep -E 'threshold|Risk' data/state/regime_monitor_latest.json`")

    lines.append("\n💡 備註：此回報屬監控性質。系統為唯讀模式，不會自動下單或修改設定。")
    return "\n".join(lines)


def skill_brake_status() -> str:
    path = REPO / "data/state/brake_health_latest.json"
    if not path.exists():
        return (
            "❌ NOT FOUND: Brake health report missing.\n"
            "💡 Hint: Please run this on your Mac:\n"
            "./.venv/bin/python scripts/brake_healthcheck.py"
        )
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"⚠️ WARN: Failed to parse brake health report: {str(e)[:50]}"
    
    results = data.get("results", [])
    if not results:
        return "⚠️ WARN: Brake health report contains no results."

    # Map results for specific display requirements
    res_map = {r["item"]: r for r in results}
    
    def get_line(item_name, label):
        r = res_map.get(item_name)
        if not r: return f"- {label}: MISSING (not in report)"
        icon = "OK" if r["status"] == "OK" else ("WARN" if r["status"] == "WARN" else "FAIL")
        return f"- {label}: {icon} ({r['note']})"

    lines = ["Brake Health (latest)"]
    lines.append(get_line("Freshness Table", "freshness"))
    lines.append(get_line("Regime Monitor", "regime"))
    
    # Run artifacts check (scan summary/selection/gate)
    arts = [r for r in results if r["item"].startswith("Backtest")]
    if not arts:
        lines.append("- artifacts: MISSING (no backtest data)")
    else:
        fails = [r["item"].split()[-1] for r in arts if r["status"] == "FAIL"]
        status = "FAIL" if fails else "OK"
        note = f"missing: {', '.join(fails)}" if fails else "all present"
        lines.append(f"- artifacts: {status} ({note})")
        
    return "\n".join(lines)


def skill_logs_tail_hint(lines: int = 60) -> str:
    n = max(20, min(120, int(lines)))
    return "\n".join([
        "你可以先看這幾個 log：",
        "• logs/launchd_daily_etl.out.log",
        "• logs/launchd_weekly_backfill.out.log",
        "• logs/launchd_dashboard.out.log",
        f"• data/state/_tg_cp/runtime.log",
        "",
        f"手動查看範例：tail -n {n} /Users/hong/Projects/HONGSTR/logs/launchd_daily_etl.out.log",
    ])


SKILL_IMPL = {
    "status_overview": lambda args: skill_status_overview(bool(args.get("include_sources", False))),
    "logs_tail_hint": lambda args: skill_logs_tail_hint(int(args.get("lines", 60))),
    "freshness_detail": lambda args: skill_freshness_detail(),
    "ml_status": lambda args: skill_ml_status(),
    "regime_status": lambda args: skill_regime_status(),
    "brake_status": lambda args: skill_brake_status(),
}


# ────────────────────── alert channel (C) ──────────────────────
def _count_pending_alerts() -> int:
    """Count unconsumed rows in alerts_pending.jsonl."""
    try:
        lines = ALERTS_PENDING.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return 0
    count = 0
    for ln in lines:
        try:
            obj = json.loads(ln)
            if not obj.get("consumed"):
                count += 1
        except Exception:
            continue
    return count


def _read_pending_alerts() -> list[dict]:
    """Return unconsumed alert records."""
    try:
        lines = ALERTS_PENDING.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    alerts = []
    for ln in lines:
        try:
            obj = json.loads(ln)
            if not obj.get("consumed"):
                alerts.append(obj)
        except Exception:
            continue
    return alerts


def _mark_alerts_consumed() -> None:
    """Rewrite alerts_pending.jsonl with all entries marked consumed (read-only fence: no delete)."""
    try:
        lines = ALERTS_PENDING.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return
    updated = []
    for ln in lines:
        try:
            obj = json.loads(ln)
            obj["consumed"] = True
            updated.append(json.dumps(obj, ensure_ascii=False))
        except Exception:
            updated.append(ln)
    try:
        ALERTS_PENDING.write_text("\n".join(updated) + "\n", encoding="utf-8")
    except Exception:
        pass


# ────────────────────── deferred followup queue ──────────────────────
_FOLLOWUP_RE = re.compile(
    r"^\[\s*FOLLOWUP\s*:\s*(\d+)\s*:\s*([^\]]{1,200})\s*\]",
    re.MULTILINE
)

def _extract_followup_tag(text: str) -> tuple[int | None, str | None, str]:
    """
    Extract [FOLLOWUP:N:topic] tag from LLM reply.
    Returns (minutes, topic, cleaned_text_without_tag).
    If no tag found, returns (None, None, original_text).
    """
    m = _FOLLOWUP_RE.search(text)
    if not m:
        return None, None, text
    minutes = int(m.group(1))
    topic = m.group(2).strip()
    # Clamp to allowed range
    minutes = max(1, min(minutes, FOLLOWUP_MAX_DELAY_MIN))
    # Remove the tag line from the user-facing reply
    cleaned = _FOLLOWUP_RE.sub("", text).strip()
    return minutes, topic, cleaned


def _enqueue_followup(chat_id: int, minutes: int, topic: str, original_msg: str) -> None:
    """Write a followup task to followup_queue.jsonl."""
    if not FOLLOWUP_ENABLED:
        return
    now = int(time.time())
    uid = hashlib.md5(f"{chat_id}{now}{topic}".encode()).hexdigest()[:6]
    ts_str = time.strftime("%Y%m%dT%H%M%S", time.gmtime(now))
    record = {
        "id": f"fq_{ts_str}_{uid}",
        "chat_id": int(chat_id),
        "created_at": now,
        "due_at": now + minutes * 60,
        "topic": topic[:200],
        "original_user_msg": (original_msg or "")[:200],
        "done": False,
    }
    _append_jsonl(FOLLOWUP_QUEUE, record)
    log_event("FOLLOWUP_QUEUED", chat_id=chat_id, due_in_min=minutes, topic=topic[:40])


def _load_due_followups() -> list[dict]:
    """Return all followup tasks that are now due (due_at <= now) and not done."""
    now = int(time.time())
    try:
        lines = FOLLOWUP_QUEUE.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    due = []
    for ln in lines:
        try:
            obj = json.loads(ln)
            if not obj.get("done") and int(obj.get("due_at", 0)) <= now:
                due.append(obj)
        except Exception:
            continue
    return due


def _mark_followups_done(ids: list[str]) -> None:
    """Mark followup records as done=True in followup_queue.jsonl."""
    if not ids:
        return
    id_set = set(ids)
    try:
        lines = FOLLOWUP_QUEUE.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return
    updated = []
    for ln in lines:
        try:
            obj = json.loads(ln)
            if obj.get("id") in id_set:
                obj["done"] = True
            updated.append(json.dumps(obj, ensure_ascii=False))
        except Exception:
            updated.append(ln)
    try:
        FOLLOWUP_QUEUE.write_text("\n".join(updated) + "\n", encoding="utf-8")
    except Exception:
        pass


def _execute_followup(task: dict) -> None:
    """Run a single due followup task: check snapshot + LLM → send."""
    chat_id = int(task.get("chat_id", 0))
    topic = task.get("topic", "系統狀態")
    original_msg = task.get("original_user_msg", "")
    created_at = task.get("created_at", int(time.time()))
    wait_min = max(1, (int(time.time()) - created_at) // 60)

    log_event("FOLLOWUP_EXEC", chat_id=chat_id, topic=topic[:40])

    system_prompt = (
        PERSONA.strip()
        + "\n\n" + _snapshot_text()
        + "\n\n[硬圍欄 — 絕對不可違反]"
        + "\n- 你是 read-only，不能執行任何指令、不能修改檔案、不能重啟服務、不能下單交易。"
        + "\n- 不可宣稱自己已執行任何動作。"
    )
    user_msg = (
        f"約 {wait_min} 分鐘前，洪老爺問過：「{original_msg}」，"
        f"你承諾了等等查看「{topic}」後主動回報。"
        f"現在請根據最新快照，用自然語氣回報你的觀察和判讀。"
        f"不需要再問問題，直接給出結論。"
    )
    body = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "options": {"temperature": 0.35},
    }
    req = urllib.request.Request(
        f"{OLLAMA_ENDPOINT}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            j = json.loads(resp.read().decode("utf-8", "ignore"))
            msg_obj = j.get("message") or {}
            txt = (msg_obj.get("content") or "").strip()
    except Exception as exc:
        log_event("FOLLOWUP_LLM_ERR", err=type(exc).__name__)
        # Fallback to raw snapshot
        txt = f"🕐 跟進報告（{wait_min} 分鐘前的問題）\n主題：{topic}\n\n{_snapshot_text()}"

    # Strip any accidental nested FOLLOWUP tags from the reply (return order: minutes, topic, cleaned)
    _, _, txt = _extract_followup_tag(txt)  # discard any new tag
    # Guardrail check
    if is_action_request(txt):
        txt = f"🕐 跟進報告：{topic}\n{_snapshot_text()[:600]}"

    cleaned = _clean_reply(txt)
    _send(chat_id, cleaned)
    log_event("FOLLOWUP_SENT", chat_id=chat_id, topic=topic[:40])


def _poll_due_followups() -> None:
    """Check followup_queue.jsonl for due tasks and execute them."""
    if not FOLLOWUP_ENABLED:
        return
    due = _load_due_followups()
    if not due:
        return
    completed_ids = []
    for task in due:
        try:
            _execute_followup(task)
            completed_ids.append(task["id"])
        except Exception as exc:
            log_event("FOLLOWUP_EXEC_ERR", id=task.get("id", "?"), err=type(exc).__name__)
            # Still mark done to avoid infinite retry on broken tasks
            completed_ids.append(task["id"])
    _mark_followups_done(completed_ids)


def _poll_and_forward_alerts() -> None:
    """Check alerts_pending.jsonl; if new alerts exist, analyze with LLM and send to all chats."""
    alerts = _read_pending_alerts()
    if not alerts:
        return

    log_event("ALERT_POLL", count=len(alerts))

    # Build a summary of the alerts for the LLM
    alert_lines = []
    for a in alerts:
        ts_str = time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(a.get("ts", 0))))
        title = a.get("title", "")
        status = a.get("status", "").upper()
        body = a.get("body", "")
        source = a.get("source", "")
        alert_lines.append(f"[{ts_str}] {status} | {title} | {body[:200]} | source={source}")

    alert_summary = "\n".join(alert_lines)
    system_prompt = (
        PERSONA.strip()
        + "\n\n" + _snapshot_text()
        + "\n\n[硬圍欄 — 絕對不可違反]"
        + "\n- 你是 read-only，不能執行任何指令、不能修改檔案、不能重嘘服務、不能下單交易。"
    )
    user_msg = (
        f"排程告警震金，以下是剛產生的 {len(alerts)} 筆系統事件：\n{alert_summary}\n"
        "請用自然語氣向洪老裴摘要說明，并提供判讀建議。"
    )

    body = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "options": {"temperature": 0.3},
    }
    req = urllib.request.Request(
        f"{OLLAMA_ENDPOINT}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            j = json.loads(resp.read().decode("utf-8", "ignore"))
            msg_obj = j.get("message") or {}
            txt = (msg_obj.get("content") or "").strip()
    except Exception as exc:
        log_event("ALERT_LLM_ERR", err=type(exc).__name__)
        # Fallback: send raw alert without LLM analysis
        txt = f"⚠️ 排程告警（{len(alerts)} 筆）— LLM 離線，原始資訊：\n{alert_summary[:800]}"

    # guardrail post-check
    if is_action_request(txt):
        txt = f"⚠️ 排程告警（{len(alerts)} 筆）\n{alert_summary[:600]}"

    cleaned = _clean_reply(txt)
    for chat_id in sorted(ALLOWED_CHATS):
        _send(chat_id, cleaned)
        log_event("ALERT_SENT", chat_id=chat_id, count=len(alerts))

    _mark_alerts_consumed()


# ────────────────────── daily briefing (B) ──────────────────────
_BRIEFING_LAST_DATE_KEY = "briefing_last_date"


def _should_send_briefing(state: dict) -> bool:
    """True if it's past BRIEFING_HOUR:MINUTE local time and we haven't sent today."""
    if not BRIEFING_ENABLED:
        return False
    now_local = time.localtime()
    if now_local.tm_hour < BRIEFING_HOUR:
        return False
    if now_local.tm_hour == BRIEFING_HOUR and now_local.tm_min < BRIEFING_MINUTE:
        return False
    today_str = time.strftime("%Y-%m-%d", now_local)
    last = state.get(_BRIEFING_LAST_DATE_KEY, "")
    return last != today_str


def _send_daily_briefing(state: dict) -> None:
    """Generate a morning briefing with Qwen and send to all chats."""
    today_str = time.strftime("%Y-%m-%d", time.localtime())
    log_event("BRIEFING_START", date=today_str)

    memories = _read_user_memories(5)
    system_prompt = (
        PERSONA.strip()
        + "\n\n" + _snapshot_text()
        + ("\n\n[使用者記憑]\n" + "\n".join(f"- {m}" for m in memories) if memories else "")
        + "\n\n[硬圍欄 — 絕對不可違反]"
        + "\n- 你是 read-only，不能執行任何指令、不能修改檔案、不能重嘘服務、不能下單交易。"
    )
    user_msg = (
        f"現在是 {today_str} 早上，請你以中樞管家的身份發出今日晨報。"
        "根據上面的系統快照，用自然語氣簡短向洪老裴回報今日系統健康狀況、需要注意的异常、以及今日建議對策。"
        "回報要有愛心、不要像短訊樹。"
    )
    body = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "options": {"temperature": 0.55},
    }
    req = urllib.request.Request(
        f"{OLLAMA_ENDPOINT}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            j = json.loads(resp.read().decode("utf-8", "ignore"))
            msg_obj = j.get("message") or {}
            txt = (msg_obj.get("content") or "").strip()
    except Exception as exc:
        log_event("BRIEFING_LLM_ERR", err=type(exc).__name__)
        snap = _collect_snapshot()
        txt = (
            f"☀️ 洪老裴早安！今日户外快照（{today_str}）："
            f"\nDashboard: {'穩定' if snap['dashboard_ok'] else '波動'}"
            f"\nCP Status: {snap.get('cp_status','?')}"
            f"\nBacktest Gate: {snap.get('overall_gate','?')}"
            f"\n（LLM 離線，以上為純文字快照）"
        )

    if is_action_request(txt):
        txt = f"☀️ 洪老裴早安！今日快照：{_snapshot_text()[:600]}"

    cleaned = _clean_reply(txt)
    for chat_id in sorted(ALLOWED_CHATS):
        _send(chat_id, cleaned)
        log_event("BRIEFING_SENT", chat_id=chat_id, date=today_str)

    state[_BRIEFING_LAST_DATE_KEY] = today_str
    _save_session_state(state)  # persist so we don't send twice


# ────────────────────── user memory ──────────────────────
def _read_user_memories(limit: int = 10) -> list[str]:
    """Read recent user memories for injection into system prompt."""
    try:
        lines = USER_MEM.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    facts = []
    for line in lines[-limit:]:
        try:
            obj = json.loads(line)
            fact = obj.get("fact", "").strip()
            if fact:
                facts.append(fact)
        except Exception:
            continue
    return facts


def _write_user_memory(chat_id: int, text: str) -> None:
    s = re.sub(r"\s+", " ", (text or "").strip())
    if len(s) > 180:
        s = s[:180] + "..."
    if s:
        _append_jsonl(USER_MEM, {"ts": int(time.time()), "chat_id": int(chat_id), "fact": s})


def _write_ops_memory(chat_id: int, user_text: str, response: str) -> None:
    fact = re.sub(r"\s+", " ", (response or "").strip())
    if len(fact) > 120:
        fact = fact[:120] + "..."
    if fact:
        _append_jsonl(OPS_MEM, {
            "ts": int(time.time()),
            "chat_id": int(chat_id),
            "user": (user_text or "")[:80],
            "fact": fact,
        })


def _memory_stats() -> tuple[int, int, list[str]]:
    def read_lines(p: Path) -> list[str]:
        try:
            return p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return []
    ops = read_lines(OPS_MEM)
    user = read_lines(USER_MEM)
    recent = []
    for line in user[-3:]:
        try:
            recent.append(json.loads(line).get("fact", ""))
        except Exception:
            continue
    return len(ops), len(user), [x for x in recent if x]


# ────────────────────── LLM (Ollama /api/chat) ──────────────────────
def _build_system_prompt() -> str:
    """Assemble the full system prompt with persona + snapshot + memories + guardrails."""
    parts = [PERSONA.strip()]

    # inject user memories
    memories = _read_user_memories(10)
    if memories:
        parts.append("\n[使用者記憶]")
        for m in memories:
            parts.append(f"- {m}")

    # inject live system snapshot
    parts.append("\n" + _snapshot_text())

    # inject available skills
    skill_lines = [f"- {s.get('name')}: {s.get('description', '')}" for s in SKILLS if s.get("type") == "read_only"]
    if skill_lines:
        parts.append("\n[可用技能（read-only）]")
        parts.extend(skill_lines)

    # instruct LLM to emit strict tags if followup is needed
    parts.append(
        "\n[延遲跟進機制 — 分鐘級別排程]"
        "\n- 如果用戶要求你「等一下告訴我」、「幫我盯著」、「過幾分鐘後回報」，"
        "\n  你 **必須** 在回覆的最後一行加上這個精確的標籤："
        "\n  [FOLLOWUP:分鐘數:你要查看的主題]"
        "\n  例如用戶說「5分鐘後告訴我 ETL 狀態」，你最後一行必須是： [FOLLOWUP:5:ETL 狀態]"
        "\n- 這是觸發系統排程的唯一方式，不可省略這行標籤！"
        "\n- 標籤會自動隱藏，不用擔心用戶看到。"
    )

    # hard guardrail reminder (redundant with persona, but explicit for safety)
    parts.append(
        "\n[硬圍欄 — 絕對不可違反]"
        "\n- 你是 read-only，不能執行任何指令、不能修改檔案、不能重啟服務、不能下單交易、不能改 repo。"
        "\n- 若使用者要求執行/修改/重啟/交易，溫和拒絕並提供手動 SOP 建議。"
        "\n- 不可宣稱自己已經執行了任何動作。"
    )

    return "\n".join(parts)


def _llm_chat(chat_id: int, user_text: str, history: list[dict]) -> tuple[str, str | None]:
    """Call Ollama /api/chat with system prompt + conversation history + new user message."""
    system_prompt = _build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]
    # Add conversation history (already contains {role, content} dicts)
    for msg in history:
        if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg.get("content", "")})
    # Add current user message
    messages.append({"role": "user", "content": user_text})

    body = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": OLLAMA_TEMPERATURE},
    }

    req = urllib.request.Request(
        f"{OLLAMA_ENDPOINT}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    log_event("LLM_REQ", chat_id=chat_id, model=OLLAMA_MODEL, history_len=len(history))
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            j = json.loads(resp.read().decode("utf-8", "ignore"))
            # /api/chat returns {"message": {"role": "assistant", "content": "..."}, ...}
            msg_obj = j.get("message") or {}
            txt = (msg_obj.get("content") or "").strip()
            ms = int((time.time() - t0) * 1000)
            log_event("LLM_RESP", chat_id=chat_id, ok=1 if txt else 0, ms=ms, bytes=len(txt.encode("utf-8")))
            return txt, None
    except Exception as exc:
        ms = int((time.time() - t0) * 1000)
        log_event("LLM_RESP", chat_id=chat_id, ok=0, ms=ms, err=type(exc).__name__)
        return "", f"{type(exc).__name__}: {exc}"


# ────────────────────── core reply (LLM-first) ──────────────────────
LLM_OFFLINE_MSG = "目前 LLM 連線中斷，稍後再試。你也可以用 /status 或 /help 查看基本資訊。"


def build_chat_reply(chat_id: int, user_text: str, use_llm: bool = True) -> tuple[str, str]:
    """Main reply builder. Returns (response_text, route_label)."""
    text = _strip_mention(user_text)

    # ── guardrail pre-check ──
    if is_action_request(text):
        resp = refusal_message()
        resp += "\n\n" + "\n".join([
            "你可以手動跑這幾條安全 SOP：",
            "• bash /Users/hong/Projects/HONGSTR/scripts/healthcheck_dashboard.sh",
            "• bash /Users/hong/Projects/HONGSTR/scripts/check_data_coverage.sh",
            "• bash /Users/hong/Projects/HONGSTR/scripts/tg_sanity.sh",
        ])
        return resp, "REFUSE"

    # ── load conversation history ──
    state = _load_session_state()
    history = _get_history(state, chat_id)

    # ── call LLM ──
    if not use_llm:
        return LLM_OFFLINE_MSG, "FALLBACK"

    snapshot = _collect_snapshot()
    use_specialist = should_use_specialist(text, snapshot)
    
    llm_resp = None
    llm_err = None
    route = "LLM"

    if use_specialist:
        logger.info(f"Routing to Reasoning Specialist: {text[:50]}...")
        # Prepare context for specialist
        specialist_prompt = f"User Query: {text}\n\nSystem Snapshot:\n{json.dumps(snapshot, indent=2)}"
        analysis = call_reasoning_specialist(specialist_prompt)
        
        if analysis:
            # Format specialist output for user (Chinese Template)
            resp_lines = [
                f"🧠 **Reasoning Specialist 診斷判讀** ({analysis.status})",
                f"**分析問題**: {analysis.problem}",
                "\n**核心發現 (Key Findings)**:",
                *[f"• {f}" for f in analysis.key_findings],
                "\n**推論假說 (Hypotheses)**:",
                *[f"• {h}" for h in analysis.hypotheses],
                "\n**建議運維 SOP (Informational Only)**:",
                *[f"• {s}" for s in analysis.recommended_next_steps],
            ]
            if analysis.risks:
                resp_lines.extend(["\n**潛在風險 (Risks)**:", *[f"• {r}" for r in analysis.risks]])
            
            # Attach citations if available
            if analysis.citations:
                resp_lines.extend(["\n**依據資料 (Citations)**:", *[f"• {c}" for c in analysis.citations]])

            llm_resp = "\n".join(resp_lines)
            route = "SPECIALIST"
        else:
            logger.warning("Specialist failed or timed out. Falling back to Snapshot reply with WARN.")
            # FALLBACK: Conservative snapshot reply marked with WARN
            lines = [
                "⚠️ **Specialist 診斷暫時不可用 (Timeout/Fail)**",
                "系統目前進入保守降級模式，以下為基礎監控快照：",
                skill_status_overview(include_sources=False)
            ]
            llm_resp = "\n".join(lines)
            route = "FALLBACK_WARN"

    if not llm_resp:
        llm_resp, llm_err = _llm_chat(chat_id, text, history)

    if llm_resp:
        # ── extract and process FOLLOWUP tag before guardrail check ──
        followup_min, followup_topic, llm_resp = _extract_followup_tag(llm_resp)

        # ── guardrail post-check: ensure LLM didn't promise to execute ──
        if is_action_request(llm_resp):
            llm_resp = refusal_message()
            followup_min = None  # discard followup if guardrail blocked

        resp = llm_resp
        # Only set LLM route if it hasn't been set (e.g. by Specialist)
        if not route or route == "LLM":
            route = "LLM"

        # ── enqueue followup if requested ──
        if followup_min and followup_topic and FOLLOWUP_ENABLED:
            _enqueue_followup(chat_id, followup_min, followup_topic, text)
    else:
        resp = LLM_OFFLINE_MSG
        route = "FALLBACK"

    # ── persist conversation history ──
    _append_history(state, chat_id, "user", text)
    _append_history(state, chat_id, "assistant", resp)
    _save_session_state(state)

    # ── write ops memory ──
    _write_ops_memory(chat_id, text, resp)

    return resp, route


# ────────────────────── commands ──────────────────────
def _run_help(skill_name: str) -> str:
    sk = SKILL_MAP.get(skill_name)
    if not sk:
        return f"找不到技能: {skill_name}\n請先用 /skills 看可用技能"
    schema = sk.get("args_schema", {})
    return "\n".join([
        f"技能: {sk.get('name')}",
        f"類型: {sk.get('type')}",
        f"說明: {sk.get('description')}",
        f"參數: {json.dumps(schema, ensure_ascii=False)}",
        f"範例: /run {skill_name} include_sources=true",
    ])


def _handle_run(text: str) -> tuple[str, bool]:
    m = re.match(r"^/run(?:@\w+)?\s*(.*)$", text)
    if not m:
        return "用法：/run <skill> [k=v ...] 或 /run help <skill>", False
    tail = (m.group(1) or "").strip()
    if not tail:
        return "用法：/run <skill> [k=v ...]，先用 /skills", False
    if tail.startswith("help "):
        name = tail.split(None, 1)[1].strip()
        return _run_help(name), True
    parts = tail.split(None, 1)
    skill_name = parts[0]
    args_raw = parts[1] if len(parts) > 1 else ""
    sk = SKILL_MAP.get(skill_name)
    if not sk or sk.get("type") != "read_only" or skill_name not in SKILL_IMPL:
        return f"找不到技能: {skill_name}\n請先用 /skills", False
    try:
        parsed = parse_args(args_raw)
        valid_args = validate(sk.get("args_schema", {}), parsed)
    except Exception as exc:
        return f"參數錯誤: {exc}\n請用 /run help {skill_name}", False
    return SKILL_IMPL[skill_name](valid_args), True


def _handle_command(chat_id: int, text: str) -> str:
    cmd = _cmd_base(text)

    if cmd == "/start":
        return (
            "嗨 👋 我是 HONGSTR 中樞管家。\n"
            "直接跟我聊就好，問什麼我都會盡量用白話回答你。\n"
            "我是 read-only 助手 — 只查看、判讀，不直接動系統。\n\n"
            "快捷指令：/status /brake /freshness /regime /ml_status /help /skills"
        )

    if cmd == "/ping":
        return "pong ✅"

    if cmd == "/help":
        return (
            "直接打字問我就好，不需要特別格式 😊\n\n"
            "📊 監控指令（read-only）：\n"
            "• /status — 系統瓶頸摘要\n"
            "• /brake — 煞車健康檢查 (Artifacts & Freshness)\n"
            "• /freshness — 資料新鮮度（3幣×3時框表格）\n"
            "• /regime — 市場機制監控（舒適圈 OK/WARN/FAIL）\n"
            "• /regime_status — 同 /regime\n"
            "• /ml_status — ML 流水線健康狀態\n"
            "• /research_status — Research Loop 今日狀態 + Leaderboard\n\n"
            "🔧 其他指令：\n"
            "• /skills /run /remember /memories /ping"
        )

    if cmd == "/status":
        return _status_short_report()

    if cmd == "/freshness":
        return skill_freshness_detail()

    if cmd == "/ml_status":
        return skill_ml_status()

    if cmd == "/regime" or cmd == "/regime_status":
        return skill_regime_status()

    if cmd == "/research_status" or cmd == "/research":
        return skill_research_status()

    if cmd == "/brake" or cmd == "/brake_status":
        return skill_brake_status()

    if cmd == "/skills":
        lines = [f"• {s.get('name')}: {s.get('description', '')}" for s in SKILLS if s.get("type") == "read_only"]
        lines.append("• (內建) /freshness: 完整的資料新鮮度表格")
        lines.append("• (內建) /ml_status: ML 流水線健康狀態")
        lines.append("• (內建) /regime: 市場機制 (舒適圈) 監控報告")
        return "可用 read-only 技能：\n" + "\n".join(lines)

    if cmd == "/run":
        out, _ = _handle_run(text)
        return out

    if cmd == "/remember":
        parts = text.split(None, 1)
        if len(parts) < 2 or not parts[1].strip():
            return "用法：/remember 你要我記住的一句話"
        _write_user_memory(chat_id, parts[1].strip())
        return "收到，已經記下來了 📝"

    if cmd == "/memories":
        ops_n, user_n, recent = _memory_stats()
        lines = [f"記憶總量：ops={ops_n} / user={user_n}"]
        if recent:
            lines.append("最近記憶：")
            for item in recent:
                lines.append(f"• {item}")
        return "\n".join(lines)

    if cmd == "/debug":
        state = _load_session_state()
        history = _get_history(state, chat_id)
        log_lines = _tail(RUNTIME_LOG, 15)
        body = [f"history_len={len(history)}", f"model={OLLAMA_MODEL}"]
        body.extend(log_lines[-10:])
        return "\n".join(body)

    if cmd == "/consult":
        return "__DELEGATE_TO_ROUTER__"

    return "不認識這個指令，用 /help 看看可以做什麼 🙂"


# ────────────────────── message handler ──────────────────────
def _handle_message(msg: dict) -> None:
    chat = msg.get("chat") or {}
    chat_id = int(chat.get("id", 0) or 0)
    msg_id = msg.get("message_id")
    text = (msg.get("text") or "").strip()
    if not text:
        return

    if text.startswith("/"):
        out = _handle_command(chat_id, text)
        if out == "__DELEGATE_TO_ROUTER__":
            # Trigger build_chat_reply for /consult
            cleaned = text.replace("/consult", "", 1).strip()
            resp, route = build_chat_reply(chat_id, cleaned, use_llm=True)
            _send(chat_id, resp, reply_to=msg_id)
            log_event("CONSULT", chat_id=chat_id, route=route)
            return
        
        _send(chat_id, out, reply_to=msg_id)
        log_event("CMD", chat_id=chat_id, cmd=_cmd_base(text) or "unknown")
        return

    cleaned = _strip_mention(text)
    resp, route = build_chat_reply(chat_id, cleaned, use_llm=True)
    _send(chat_id, resp, reply_to=msg_id)
    log_event("CHAT", chat_id=chat_id, route=route)


# ────────────────────── main loop ──────────────────────
def main() -> None:
    _ensure_state()

    if not TG_BOT_TOKEN:
        log_event("START", ok=0, reason="missing_token")
        return
    if not ALLOWED_CHATS:
        log_event("START", ok=0, reason="missing_allowlist")
        return

    log_event("START", ok=1, model=OLLAMA_MODEL, allowed_chats=",".join(str(x) for x in sorted(ALLOWED_CHATS)))

    offset = _load_offset()
    _save_offset(offset)
    err_backoff = 0  # consecutive error count for backoff

    while True:
        data = _get_updates(offset)

        # handle errors with exponential backoff
        http_err = data.get("_http_error")
        if http_err or not data.get("ok", True):
            err_backoff = min(err_backoff + 1, 6)
            wait = min(5 * (2 ** (err_backoff - 1)), 30)
            log_event("BACKOFF", seconds=wait, consecutive_errors=err_backoff)
            time.sleep(wait)
            continue

        err_backoff = 0  # reset on success

        # ── (C) alert channel: check for pending alerts from scheduled jobs ──
        try:
            _poll_and_forward_alerts()
        except Exception as exc:
            log_event("ALERT_POLL_ERR", err=type(exc).__name__)

        # ── (B) daily briefing: send morning report if due ──
        try:
            state = _load_session_state()
            if _should_send_briefing(state):
                _send_daily_briefing(state)
        except Exception as exc:
            log_event("BRIEFING_ERR", err=type(exc).__name__)

        # ── (D) deferred followup queue: execute due tasks ──
        try:
            _poll_due_followups()
        except Exception as exc:
            log_event("FOLLOWUP_POLL_ERR", err=type(exc).__name__)

        items = data.get("result") or []
        if not isinstance(items, list):
            items = []

        if not items:
            _save_offset(offset)
            time.sleep(0.5)
            continue

        for item in items:
            update_id = int(item.get("update_id", 0) or 0)
            if update_id:
                offset = max(offset, update_id + 1)

            msg = item.get("message") or item.get("edited_message") or item.get("channel_post") or {}
            if not msg:
                continue
            if not _chat_allowed(msg):
                continue

            try:
                _handle_message(msg)
            except Exception as exc:
                log_event("HANDLE_ERR", err=type(exc).__name__)

        _save_offset(offset)


if __name__ == "__main__":
    main()
