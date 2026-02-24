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
    token = (text or "").strip().split()[0] if (text or "").strip() else ""
    if not token.startswith("/"):
        return ""
    return token.split("@")[0].lower()


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

    # pending alerts count
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
        "pending_alerts": pending_alerts,
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
    
    for sym in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
        sym_data = snap["freshness"].get(sym, {})
        tf_parts = []
        for tf in ["1m", "1h", "4h"]:
            d = sym_data.get(tf, {})
            age = d.get("age_hours")
            age_str = f"{age:.1f}h" if age is not None else "缺失"
            tf_parts.append(f"{tf}:{age_str}")
        lines.append(f"• {sym}: {' / '.join(tf_parts)}")
    if include_sources:
        lines.append("依據: logs/launchd_dashboard.out.log, logs/launchd_daily_etl.out.log")
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
    if use_llm:
        llm_resp, llm_err = _llm_chat(chat_id, text, history)
    else:
        llm_resp, llm_err = "", "LLM disabled"

    if llm_resp:
        # ── extract and process FOLLOWUP tag before guardrail check ──
        followup_min, followup_topic, llm_resp = _extract_followup_tag(llm_resp)

        # ── guardrail post-check: ensure LLM didn't promise to execute ──
        if is_action_request(llm_resp):
            llm_resp = refusal_message()
            followup_min = None  # discard followup if guardrail blocked

        resp = llm_resp
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
            "快捷指令：/status /help /skills /remember"
        )

    if cmd == "/ping":
        return "pong ✅"

    if cmd == "/help":
        return (
            "直接打字問我就好，不需要特別格式 😊\n"
            "常用快捷：/status /skills /run /remember /memories /ping"
        )

    if cmd == "/status":
        return skill_status_overview(include_sources=True)

    if cmd == "/skills":
        lines = [f"• {s.get('name')}: {s.get('description', '')}" for s in SKILLS if s.get("type") == "read_only"]
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
