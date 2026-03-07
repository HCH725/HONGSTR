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

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("tg_cp_server")

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
    from _local.telegram_cp.prompt_pack import build_system_prompt as build_prompt_pack_system_prompt  # type: ignore
except Exception:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from prompt_pack import build_system_prompt as build_prompt_pack_system_prompt  # type: ignore
    except Exception:
        build_prompt_pack_system_prompt = None  # type: ignore

try:
    from _local.telegram_cp.router import should_use_specialist
    from _local.telegram_cp.reasoning_client import call_reasoning_specialist
except Exception:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from router import should_use_specialist
    from reasoning_client import call_reasoning_specialist

try:
    from _local.telegram_cp.skills.incident_timeline_builder import build_incident_timeline
except Exception:
    sys.path.insert(0, str(Path(__file__).resolve().parent / "skills"))
    from incident_timeline_builder import build_incident_timeline
    from system_health_morning_brief import get_morning_brief
    from config_drift_auditor import audit_config_drift
    from data_freshness_watchdog_report import get_freshness_report
    from execution_quality_report_readonly import get_execution_quality_report
    from backtest_reproducibility_audit import audit_backtest_reproducibility
    from factor_health_and_drift_report import get_factor_health_report
    from strategy_regime_sensitivity_report import get_strategy_sensitivity_report

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
TG_PROMPT_PACK_ENABLED = os.environ.get("TG_PROMPT_PACK_ENABLED", "1") != "0"
MAX_REPLY_CHARS = int(os.environ.get("HONGSTR_TG_MAX_REPLY_CHARS", "1800"))
HISTORY_MAX_TURNS = int(os.environ.get("HONGSTR_TG_HISTORY_TURNS", "10"))

# Daily briefing schedule (local time)
BRIEFING_HOUR = int(os.environ.get("HONGSTR_BRIEFING_HOUR", "8"))
BRIEFING_MINUTE = int(os.environ.get("HONGSTR_BRIEFING_MINUTE", "30"))
BRIEFING_ENABLED = os.environ.get("HONGSTR_BRIEFING_ENABLED", "1") != "0"

# Deferred followup config
FOLLOWUP_MAX_DELAY_MIN = int(os.environ.get("HONGSTR_FOLLOWUP_MAX_MIN", "60"))
FOLLOWUP_ENABLED = os.environ.get("HONGSTR_FOLLOWUP_ENABLED", "1") != "0"
REGIME_MONITOR_FRESH_OK_H = float(os.environ.get("HONGSTR_REGIME_MONITOR_FRESH_OK_H", "12"))

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


def _status_health_pack_path() -> Path:
    return REPO / "data/state/system_health_latest.json"


def _status_ssot_sources_line() -> str:
    return "Sources: system_health_latest.json"


def _status_refresh_hint() -> str:
    return "bash scripts/refresh_state.sh"


def _status_unknown_report(missing: list[str], unreadable: list[str]) -> str:
    miss = ", ".join(sorted(set(missing))) if missing else "none"
    bad = ", ".join(sorted(set(unreadable))) if unreadable else "none"
    return "\n".join(
        [
            "SSOT_STATUS: UNKNOWN",
            "SSOT_SEMANTICS: SystemHealth only",
            f"Issues: missing=[{miss}] unreadable=[{bad}]",
            "Freshness: UNKNOWN",
            "CoverageMatrix: UNKNOWN",
            "Brake: UNKNOWN",
            "RegimeMonitor: UNKNOWN",
            f"RefreshHint: Run: `{_status_refresh_hint()}`",
            _status_ssot_sources_line(),
        ]
    )


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


def _normalize_regime_signal_status(status_raw: object) -> str:
    status = str(status_raw or "UNKNOWN").upper().strip()
    if status not in {"OK", "WARN", "FAIL"}:
        return "UNKNOWN"
    return status


def _normalize_coverage_status(status_raw: object) -> str:
    status = str(status_raw or "UNKNOWN").upper().strip()
    if status in {"PASS", "OK", "DONE"}:
        return "PASS"
    if status in {"WARN", "IN_PROGRESS"}:
        return "WARN"
    if status in {"FAIL", "BLOCKED", "BLOCKED_DATA_QUALITY"}:
        return "FAIL"
    if status == "NEEDS_REBASE":
        return "NEEDS_REBASE"
    return "UNKNOWN"


def _coverage_health_status(
    row_statuses: list[object],
    *,
    blocked_count: int = 0,
    rebase_count: int = 0,
    total_count: int | None = None,
) -> str:
    normalized = [_normalize_coverage_status(s) for s in row_statuses]
    total = len(normalized) if total_count is None else int(total_count)

    if total <= 0 and blocked_count <= 0 and rebase_count <= 0:
        return "UNKNOWN"
    if blocked_count > 0 or "FAIL" in normalized:
        return "FAIL"
    if rebase_count > 0 or "NEEDS_REBASE" in normalized:
        return "WARN"
    if "WARN" in normalized:
        return "WARN"
    if "PASS" in normalized:
        return "PASS"
    return "UNKNOWN"


def _fmt_num(v: float | int | None) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.1f}"
    except Exception:
        return "N/A"


def _daily_report_path() -> Path:
    return REPO / "data/state/daily_report_latest.json"


def _daily_unknown(value: object, *, digits: int = 2) -> str:
    try:
        if value is None:
            return "資料不足/UNKNOWN"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "資料不足/UNKNOWN"


def _daily_int_or_unknown(value: object) -> str:
    try:
        if value is None:
            return "資料不足/UNKNOWN"
        return str(int(value))
    except Exception:
        return "資料不足/UNKNOWN"


def _daily_acronym_map() -> dict[str, str]:
    defaults = {
        "SSOT": "單一真實來源",
        "DD": "回撤（Drawdown）",
        "MDD": "最大回撤（Max Drawdown）",
        "Sharpe": "風險調整後報酬",
        "Trades": "交易筆數",
        "OOS": "樣本外（Out-of-Sample）",
        "IS": "樣本內（In-Sample）",
        "OOS/IS": "樣本外/樣本內",
        "WF": "滾動前推驗證（Walk-Forward）",
        "L1": "低優先級處置",
        "L2": "中優先級處置",
        "L3": "高優先級處置",
        "L1/L2/L3": "低/中/高優先級風險分層",
        "TP": "停利（Take Profit）",
        "SL": "停損（Stop Loss）",
        "DCA": "定期定額/分批攤平（Dollar-Cost Averaging）",
    }
    path = REPO / "docs/ops/acronym_glossary_zh.md"
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return defaults

    for line in content.splitlines():
        ln = line.strip().lstrip("-").strip()
        if not ln or ":" not in ln:
            continue
        key, val = ln.split(":", 1)
        key_norm = key.strip()
        val_norm = val.strip()
        if key_norm in defaults and val_norm:
            defaults[key_norm] = val_norm
    return defaults


def _daily_trim(text: str, limit: int = 180) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)] + "…"


def _daily_norm_status(status_raw: object) -> str:
    status = str(status_raw or "UNKNOWN").upper().strip()
    if status in {"OK", "WARN", "FAIL", "UNKNOWN"}:
        return status
    if status in {"PASS", "DONE"}:
        return "OK"
    if status == "NEEDS_REBASE":
        return "WARN"
    return "UNKNOWN"


def _daily_int(value: object, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _daily_reason(default_reason: str, llm_note: str | None) -> str:
    if isinstance(llm_note, str) and llm_note.strip():
        return _daily_trim(llm_note.strip())
    return _daily_trim(default_reason)


def _daily_next_step(
    status: str,
    *,
    ok: str,
    warn: str,
    fail: str,
    unknown: str,
) -> str:
    normalized = _daily_norm_status(status)
    if normalized == "OK":
        return ok
    if normalized == "WARN":
        return warn
    if normalized == "FAIL":
        return fail
    return unknown


def _daily_acr_short(desc: str) -> str:
    text = str(desc or "").strip()
    for marker in ("（", "("):
        pos = text.find(marker)
        if pos > 0:
            text = text[:pos].strip()
            break
    return text or "資料不足"


def _daily_load_payload() -> tuple[dict, str | None]:
    path = _daily_report_path()
    if not path.exists():
        return (
            {
                "schema": {},
                "generated_utc": "",
                "refresh_hint": _status_refresh_hint(),
                "ssot_status": "UNKNOWN",
                "ssot_components": {},
                "freshness_summary": {
                    "counts": {"OK": 0, "WARN": 0, "FAIL": 0, "UNKNOWN": 0},
                    "profile_totals": {"realtime": 0, "backtest": 0},
                    "total_rows": 0,
                    "max_age_h": None,
                    "top_offenders": [],
                },
                "latest_backtest_head": {
                    "status": "UNKNOWN",
                    "metrics_status": "UNKNOWN",
                    "metrics": {
                        "final_score": None,
                        "oos_sharpe": None,
                        "oos_mdd": None,
                        "is_sharpe": None,
                        "trades_count": None,
                    },
                    "gate": {"overall": "UNKNOWN"},
                },
                "strategy_pool": {
                    "summary": {"counts": {"candidates": 0, "promoted": 0, "demoted": 0}},
                    "leaderboard_top": [],
                    "direction_coverage": {
                        "counts": {"long": 0, "short": 0, "longshort": 0, "unknown": 0},
                        "short_coverage": {
                            "candidates": 0,
                            "gate_pass": 0,
                            "best_entry": None,
                            "best_entry_reason": "missing_ssot",
                        },
                    },
                },
                "governance": {
                    "overfit_gates_policy": {"name": "UNKNOWN"},
                    "today_gate_summary": {"date_utc": "", "scope": "missing_ssot", "total": 0, "pass": 0, "warn": 0, "fail": 0, "unknown": 0},
                },
                "guardrails": {
                    "status": "WARN",
                    "checks": {
                        "core_diff_src_hongstr": {"status": "PASS_EXPECTED"},
                        "tg_cp_no_exec": {"status": "PASS_EXPECTED"},
                        "no_data_committed": {"status": "PASS_EXPECTED"},
                    },
                },
            },
            "missing_daily_report_ssot",
        )

    payload = _load_json(path, {})
    if not isinstance(payload, dict) or not payload:
        payload = {
            "schema": {},
            "generated_utc": "",
            "refresh_hint": _status_refresh_hint(),
            "ssot_status": "UNKNOWN",
            "ssot_components": {},
            "freshness_summary": {
                "counts": {"OK": 0, "WARN": 0, "FAIL": 0, "UNKNOWN": 0},
                "profile_totals": {"realtime": 0, "backtest": 0},
                "total_rows": 0,
                "max_age_h": None,
                "top_offenders": [],
            },
                "latest_backtest_head": {"status": "UNKNOWN", "metrics_status": "UNKNOWN", "metrics": {}, "gate": {"overall": "UNKNOWN"}},
                "strategy_pool": {
                    "summary": {"counts": {"candidates": 0, "promoted": 0, "demoted": 0}},
                    "leaderboard_top": [],
                    "direction_coverage": {
                        "counts": {"long": 0, "short": 0, "longshort": 0, "unknown": 0},
                        "short_coverage": {
                            "candidates": 0,
                            "gate_pass": 0,
                            "best_entry": None,
                            "best_entry_reason": "invalid_ssot",
                        },
                    },
                },
                "governance": {
                    "overfit_gates_policy": {"name": "UNKNOWN"},
                    "today_gate_summary": {"date_utc": "", "scope": "invalid_ssot", "total": 0, "pass": 0, "warn": 0, "fail": 0, "unknown": 0},
                },
            "guardrails": {
                "status": "WARN",
                "checks": {
                    "core_diff_src_hongstr": {"status": "PASS_EXPECTED"},
                    "tg_cp_no_exec": {"status": "PASS_EXPECTED"},
                    "no_data_committed": {"status": "PASS_EXPECTED"},
                },
            },
        }
        return payload, "unreadable_daily_report_ssot"
    return payload, None


def _daily_compose_report(
    payload: dict,
    *,
    status: str,
    note: str | None = None,
    llm_notes: list[str] | None = None,
) -> str:
    refresh_hint = str(payload.get("refresh_hint") or _status_refresh_hint())
    generated_utc = str(payload.get("generated_utc") or "資料不足/UNKNOWN")
    ssot_status = _daily_norm_status(payload.get("ssot_status"))
    acr = _daily_acronym_map()
    acr_short = {k: _daily_acr_short(v) for k, v in acr.items()}
    acr_display = {
        "SSOT": acr_short.get("SSOT") or "單一真實來源",
        "DD": "回撤",
        "MDD": "最大回撤",
        "Sharpe": "風險報酬",
        "Trades": "交易筆數",
        "OOS": "樣本外",
        "IS": "樣本內",
        "WF": "滾動驗證",
        "L1/L2/L3": "低中高優先",
        "TP": "停利",
        "SL": "停損",
        "DCA": "分批攤平",
    }

    components = payload.get("ssot_components", {})
    if not isinstance(components, dict):
        components = {}
    freshness_comp = components.get("freshness", {}) if isinstance(components.get("freshness"), dict) else {}
    coverage_comp = components.get("coverage_matrix", {}) if isinstance(components.get("coverage_matrix"), dict) else {}
    brake_comp = components.get("brake", {}) if isinstance(components.get("brake"), dict) else {}
    regime_comp = components.get("regime_monitor", {}) if isinstance(components.get("regime_monitor"), dict) else {}
    regime_signal_comp = components.get("regime_signal", {}) if isinstance(components.get("regime_signal"), dict) else {}
    fresh_component_status = _daily_norm_status(freshness_comp.get("status"))
    coverage_component_status = _daily_norm_status(coverage_comp.get("status"))
    brake_component_status = _daily_norm_status(brake_comp.get("status"))
    regime_monitor_status = _daily_norm_status(regime_comp.get("status"))
    regime_signal_status = _daily_norm_status(regime_signal_comp.get("status"))
    regime_signal_reason_raw = regime_signal_comp.get("top_reason")
    regime_signal_reason = "資料不足/UNKNOWN"
    if isinstance(regime_signal_reason_raw, str) and regime_signal_reason_raw.strip():
        regime_signal_reason = regime_signal_reason_raw.strip()
    regime_threshold_value = _daily_unknown(regime_signal_comp.get("threshold_value"), digits=4)
    regime_threshold_source_path = str(regime_signal_comp.get("threshold_source_path") or "").strip() or "資料不足/UNKNOWN"
    regime_threshold_policy_sha_raw = str(regime_signal_comp.get("threshold_policy_sha") or "").strip()
    regime_threshold_policy_sha = regime_threshold_policy_sha_raw[:12] if regime_threshold_policy_sha_raw else "資料不足/UNKNOWN"
    regime_threshold_rationale = str(regime_signal_comp.get("threshold_rationale") or "").strip() or "資料不足/UNKNOWN"
    regime_calibration_status_raw = str(regime_signal_comp.get("calibration_status") or "").upper().strip()
    regime_calibration_status = regime_calibration_status_raw if regime_calibration_status_raw in {"OK", "WARN", "STALE", "UNKNOWN"} else "UNKNOWN"
    regime_last_calibrated_raw = regime_signal_comp.get("last_calibrated_utc")
    regime_last_calibrated = str(regime_last_calibrated_raw).strip() if isinstance(regime_last_calibrated_raw, str) and str(regime_last_calibrated_raw).strip() else "資料不足/UNKNOWN"
    system_section_status = _status_max(ssot_status, regime_signal_status)
    if regime_calibration_status == "STALE":
        system_section_status = _status_max(system_section_status, "WARN")
    regime_signal_reason_short = _daily_trim(regime_signal_reason, limit=24)
    regime_threshold_source_short = _daily_trim(regime_threshold_source_path, limit=72)
    regime_threshold_rationale_short = _daily_trim(regime_threshold_rationale, limit=28)
    if regime_signal_status == "FAIL":
        regime_reason_zh_note = "口語補註=風險已越過紅線，代表短期回撤擴大。"
    elif regime_signal_status == "WARN":
        regime_reason_zh_note = "口語補註=風險正在升溫，需先收斂曝險。"
    else:
        regime_reason_zh_note = "口語補註=目前在風險舒適區。"
    if regime_calibration_status == "OK":
        regime_calibration_note = f"校準狀態=OK（週校準有效）；上次校準={regime_last_calibrated}。"
    elif regime_calibration_status == "WARN":
        regime_calibration_note = f"校準狀態=WARN（樣本偏少，建議人工覆核）；上次校準={regime_last_calibrated}。"
    elif regime_calibration_status == "STALE":
        regime_calibration_note = f"校準狀態=STALE（超過週期，建議重跑校準）；上次校準={regime_last_calibrated}。"
    else:
        regime_calibration_note = f"校準狀態=UNKNOWN（資料不足）；上次校準={regime_last_calibrated}。"

    freshness_summary = payload.get("freshness_summary", {})
    if not isinstance(freshness_summary, dict):
        freshness_summary = {}
    fresh_counts = freshness_summary.get("counts", {})
    if not isinstance(fresh_counts, dict):
        fresh_counts = {}
    profile_totals = freshness_summary.get("profile_totals", {})
    if not isinstance(profile_totals, dict):
        profile_totals = {}
    offenders = freshness_summary.get("top_offenders", [])
    if not isinstance(offenders, list):
        offenders = []
    top_offender = offenders[0] if offenders and isinstance(offenders[0], dict) else {}
    fresh_ok = _daily_int(fresh_counts.get("OK"))
    fresh_warn = _daily_int(fresh_counts.get("WARN"))
    fresh_fail = _daily_int(fresh_counts.get("FAIL"))
    fresh_unknown = _daily_int(fresh_counts.get("UNKNOWN"))
    fresh_total = _daily_int(freshness_summary.get("total_rows"))
    if fresh_fail > 0:
        freshness_status = "FAIL"
    elif fresh_warn > 0 or fresh_unknown > 0:
        freshness_status = "WARN"
    elif fresh_total > 0:
        freshness_status = "OK"
    else:
        freshness_status = fresh_component_status

    backtest = payload.get("latest_backtest_head", {})
    if not isinstance(backtest, dict):
        backtest = {}
    bt_metrics = backtest.get("metrics", {})
    if not isinstance(bt_metrics, dict):
        bt_metrics = {}
    bt_gate = backtest.get("gate", {})
    if not isinstance(bt_gate, dict):
        bt_gate = {}
    bt_status = _daily_norm_status(backtest.get("status"))
    bt_gate_status_raw = str(bt_gate.get("overall") or "UNKNOWN").upper()
    bt_gate_status = _daily_norm_status(bt_gate_status_raw)
    bt_metrics_status = _daily_norm_status(backtest.get("metrics_status"))
    if bt_status == "FAIL" or bt_gate_status == "FAIL":
        backtest_status = "FAIL"
    elif bt_status == "UNKNOWN":
        backtest_status = "UNKNOWN"
    elif bt_gate_status == "WARN" or bt_metrics_status in {"WARN", "UNKNOWN"}:
        backtest_status = "WARN"
    else:
        backtest_status = "OK"
    sources = payload.get("sources", {})
    if not isinstance(sources, dict):
        sources = {}
    worker_source = sources.get("worker_inbox", {})
    if not isinstance(worker_source, dict):
        worker_source = {}
    worker_present = bool(worker_source.get("present"))
    worker_note = str(worker_source.get("note") or "").strip()
    bt_source_raw = str(backtest.get("source") or "local").strip().lower()
    bt_source = "worker_inbox" if bt_source_raw == "worker_inbox" else "local"
    bt_path = str(backtest.get("path") or "").strip()
    bt_bundle = str(backtest.get("bundle") or "").strip()
    if bt_source == "worker_inbox":
        worker_token = bt_bundle
        if not worker_token and bt_path:
            worker_token = Path(bt_path).parent.name or Path(bt_path).name
        backtest_source_line = f"來源：WORKER {worker_token or '資料不足/UNKNOWN'}"
    else:
        local_token = ""
        if bt_path:
            local_token = Path(bt_path).parent.name or Path(bt_path).name
        if not local_token:
            local_token = str(backtest.get("candidate_id") or "資料不足/UNKNOWN")
        backtest_source_line = f"來源：LOCAL {local_token}"
        if worker_present and worker_note:
            backtest_source_line += f"（{worker_note}）"

    strategy_pool = payload.get("strategy_pool", {})
    if not isinstance(strategy_pool, dict):
        strategy_pool = {}
    pool_summary = strategy_pool.get("summary", {})
    if not isinstance(pool_summary, dict):
        pool_summary = {}
    pool_counts = pool_summary.get("counts", {})
    if not isinstance(pool_counts, dict):
        pool_counts = {}
    top_entries = strategy_pool.get("leaderboard_top", [])
    if not isinstance(top_entries, list):
        top_entries = []
    top_entry = top_entries[0] if top_entries and isinstance(top_entries[0], dict) else {}
    top_entry_status = _daily_norm_status(top_entry.get("metrics_status"))
    top_entry_gate = _daily_norm_status(top_entry.get("gate_overall"))
    direction_coverage = strategy_pool.get("direction_coverage", {})
    if not isinstance(direction_coverage, dict):
        direction_coverage = {}
    direction_counts = direction_coverage.get("counts", {})
    if not isinstance(direction_counts, dict):
        direction_counts = {}
    short_coverage = direction_coverage.get("short_coverage", {})
    if not isinstance(short_coverage, dict):
        short_coverage = {}
    short_best = short_coverage.get("best_entry", {})
    if not isinstance(short_best, dict):
        short_best = {}
    short_best_status = _daily_norm_status(short_best.get("metrics_status"))
    pool_candidates = _daily_int(pool_counts.get("candidates"))
    short_candidates = _daily_int(short_coverage.get("candidates"))
    if pool_candidates <= 0:
        strategy_status = "UNKNOWN"
    elif top_entry_gate == "FAIL":
        strategy_status = "WARN"
    elif top_entry_status in {"WARN", "UNKNOWN"}:
        strategy_status = "WARN"
    elif short_candidates > 0 and short_best_status in {"WARN", "UNKNOWN"}:
        strategy_status = "WARN"
    else:
        strategy_status = "OK"

    governance = payload.get("governance", {})
    if not isinstance(governance, dict):
        governance = {}
    policy = governance.get("overfit_gates_policy", {})
    if not isinstance(policy, dict):
        policy = {}
    gate_summary = governance.get("today_gate_summary", {})
    if not isinstance(gate_summary, dict):
        gate_summary = {}
    gate_pass = _daily_int(gate_summary.get("pass"))
    gate_warn = _daily_int(gate_summary.get("warn"))
    gate_fail = _daily_int(gate_summary.get("fail"))
    gate_unknown = _daily_int(gate_summary.get("unknown"))
    gate_total = _daily_int(gate_summary.get("total"))
    if gate_fail > 0:
        governance_status = "FAIL"
    elif gate_warn > 0 or gate_unknown > 0:
        governance_status = "WARN"
    elif gate_total > 0 or gate_pass > 0:
        governance_status = "OK"
    else:
        governance_status = "UNKNOWN"

    guardrails = payload.get("guardrails", {})
    if not isinstance(guardrails, dict):
        guardrails = {}
    guardrails_checks = guardrails.get("checks", {})
    if not isinstance(guardrails_checks, dict):
        guardrails_checks = {}
    core_diff_status = str((guardrails_checks.get("core_diff_src_hongstr") or {}).get("status", "UNKNOWN")).upper()
    no_exec_status = str((guardrails_checks.get("tg_cp_no_exec") or {}).get("status", "UNKNOWN")).upper()
    no_data_status = str((guardrails_checks.get("no_data_committed") or {}).get("status", "UNKNOWN")).upper()
    guardrail_values = [core_diff_status, no_exec_status, no_data_status]
    if any(v == "FAIL" for v in guardrail_values):
        guardrails_status = "FAIL"
    elif any(v in {"UNKNOWN", "WARN"} for v in guardrail_values):
        guardrails_status = "WARN"
    else:
        guardrails_status = _daily_norm_status(guardrails.get("status"))
        if guardrails_status == "UNKNOWN":
            guardrails_status = "WARN"

    llm_notes = llm_notes or []
    while len(llm_notes) < 6:
        llm_notes.append("")

    regime_signal_reason_cn = (
        f"RegimeSignal（市場風險告警）={regime_signal_status}；"
        f"{regime_calibration_note}"
        f"；"
        f"來源={regime_threshold_source_short}；"
        f"版本={regime_threshold_policy_sha}；"
        f"門檻={regime_threshold_value}；"
        f"{regime_reason_zh_note}"
        f"；"
        f"原因={regime_signal_reason_short}；"
        f"理由={regime_threshold_rationale_short}。"
    )
    system_reason = (
        f"{regime_signal_reason_cn} "
        f"SSOT={ssot_status}；Freshness={fresh_component_status}、Coverage={coverage_component_status}、"
        f"Brake={brake_component_status}、RegimeMonitor={regime_monitor_status}。"
    )
    offender_text = "資料不足/UNKNOWN"
    if isinstance(top_offender, dict) and top_offender:
        offender_text = (
            f"{top_offender.get('symbol','UNKNOWN')} {top_offender.get('tf','UNKNOWN')}"
            f"[{top_offender.get('profile','UNKNOWN')}] age_h={_daily_unknown(top_offender.get('age_h'), digits=1)}"
        )
    freshness_reason = (
        f"rows={_daily_int_or_unknown(freshness_summary.get('total_rows'))}；"
        f"OK/WARN/FAIL/UNKNOWN={_daily_int_or_unknown(fresh_counts.get('OK'))}/"
        f"{_daily_int_or_unknown(fresh_counts.get('WARN'))}/"
        f"{_daily_int_or_unknown(fresh_counts.get('FAIL'))}/"
        f"{_daily_int_or_unknown(fresh_counts.get('UNKNOWN'))}；"
        f"max_age_h={_daily_unknown(freshness_summary.get('max_age_h'), digits=1)}；"
        f"top_offender={offender_text}。"
    )
    backtest_reason = (
        f"cand={backtest.get('candidate_id','UNKNOWN')}[{backtest.get('direction','UNKNOWN')}]；"
        f"gate={bt_gate_status_raw}；score={_daily_unknown(bt_metrics.get('final_score'))}；"
        f"OOS={_daily_unknown(bt_metrics.get('oos_sharpe'))}；MDD={_daily_unknown(bt_metrics.get('oos_mdd'))}；"
        f"IS={_daily_unknown(bt_metrics.get('is_sharpe'))}；Trades={_daily_int_or_unknown(bt_metrics.get('trades_count'))}；"
        f"metrics={backtest.get('metrics_status','UNKNOWN')}。"
    )
    short_best_name = short_best.get("strategy_id") or "資料不足/UNKNOWN"
    if short_best_name == "資料不足/UNKNOWN":
        short_best_summary = "資料不足/UNKNOWN"
    else:
        short_best_summary = (
            f"{short_best_name}(score={_daily_unknown(short_best.get('score'))},"
            f"metrics={short_best.get('metrics_status','UNKNOWN')})"
        )
    strategy_reason = (
        f"SHORT覆蓋 候選={_daily_int_or_unknown(short_coverage.get('candidates'))}/"
        f"過gate={_daily_int_or_unknown(short_coverage.get('gate_pass'))}/"
        f"最佳={short_best_summary}；"
        f"counts={_daily_int_or_unknown(pool_counts.get('candidates'))}/"
        f"{_daily_int_or_unknown(pool_counts.get('promoted'))}/"
        f"{_daily_int_or_unknown(pool_counts.get('demoted'))}；"
        f"Top1={top_entry.get('strategy_id','UNKNOWN')}[{top_entry.get('direction','UNKNOWN')}]"
        f"(score={_daily_unknown(top_entry.get('score'))},m={top_entry.get('metrics_status','UNKNOWN')})。"
    )
    governance_reason = (
        f"policy={policy.get('name','UNKNOWN')}；gate pass/warn/fail/unknown="
        f"{_daily_int_or_unknown(gate_summary.get('pass'))}/"
        f"{_daily_int_or_unknown(gate_summary.get('warn'))}/"
        f"{_daily_int_or_unknown(gate_summary.get('fail'))}/"
        f"{_daily_int_or_unknown(gate_summary.get('unknown'))}"
        f" (scope={gate_summary.get('scope','UNKNOWN')})。"
    )
    guardrails_reason = (
        f"core diff={core_diff_status}；tg_cp no-exec={no_exec_status}；"
        f"no data committed={no_data_status}。"
    )
    system_next_default = _daily_next_step(
        system_section_status,
        ok="L1：維持排程，明天同一時間再看 /daily。",
        warn="L2：先跑 refresh_state，再優先排查 DataFreshness 與 Guardrails。",
        fail="L3：先停新增研究輸出，照 operator manual 逐項排查紅燈。",
        unknown="L2：先確認 daily_report_latest.json 與 system_health_latest.json 可讀。",
    )
    if regime_signal_status == "FAIL":
        system_next = "L3：RegimeSignal（市場風險告警）紅燈；先降槓桿或降部位、暫停 promote，改看 short 候選並重跑 gate。"
    elif regime_signal_status == "WARN":
        system_next = "L2：RegimeSignal（市場風險告警）轉黃；先小幅降槓桿、暫停 promote，優先檢查 short 候選。"
    elif regime_calibration_status == "STALE":
        system_next = "L2：Regime 門檻校準已過期；先跑 calibrate_regime_thresholds 並開 policy PR，審核後再生效。"
    else:
        system_next = system_next_default

    sections = [
        {
            "title": "SystemHealth",
            "status": system_section_status,
            "reason": _daily_reason(system_reason, llm_notes[0]),
            "next": system_next,
        },
        {
            "title": "DataFreshness",
            "status": freshness_status,
            "reason": _daily_reason(freshness_reason, llm_notes[1]),
            "next": _daily_next_step(
                freshness_status,
                ok="L1：維持 refresh_state 排程，異常時再看 offender。",
                warn="L2：先看 top offender 的 ETL 與檔案時間戳，確認 age_h 下降。",
                fail="L3：先補資料來源後重跑 refresh_state，再確認 FAIL 清零。",
                unknown="L2：確認 freshness_summary 欄位存在且型別正確。",
            ),
        },
        {
            "title": "Backtest",
            "status": backtest_status,
            "source_line": backtest_source_line,
            "reason": _daily_reason(backtest_reason, llm_notes[2]),
            "next": _daily_next_step(
                backtest_status,
                ok="L1：維持觀察；若連兩日下滑再進 governance 複查。",
                warn="L2：重跑 research loop(one-shot)並核對 metrics_status/reason。",
                fail="L3：先凍結該候選推進，先解 gate fail 原因再評估。",
                unknown="L2：確認 latest_backtest_head artifacts 與 metrics 是否齊全。",
            ),
        },
        {
            "title": "StrategyPool+Leaderboard",
            "status": strategy_status,
            "reason": _daily_reason(strategy_reason, llm_notes[3]),
            "next": _daily_next_step(
                strategy_status,
                ok="L1：維持方向覆蓋；追蹤 SHORT 最佳候選是否穩定。",
                warn="L2：補齊缺失 metrics 或方向欄位，再更新 leaderboard。",
                fail="L3：先停止策略池升級流程，先修正 ranking/gate 異常。",
                unknown="L2：先確認 strategy_pool summary 與 leaderboard_top 來源完整。",
            ),
        },
        {
            "title": "Governance(Overfit)",
            "status": governance_status,
            "reason": _daily_reason(governance_reason, llm_notes[4]),
            "next": _daily_next_step(
                governance_status,
                ok="L1：照既有 overfit policy 持續監控即可。",
                warn="L2：把 WARN/UNKNOWN 候選列入 watchlist 並補原因標註。",
                fail="L3：針對 fail 候選先做原因分群，再決定是否降級。",
                unknown="L2：確認 today_gate_summary 是否由最新研究輸出更新。",
            ),
        },
        {
            "title": "Guardrails",
            "status": guardrails_status,
            "reason": _daily_reason(guardrails_reason, llm_notes[5]),
            "next": _daily_next_step(
                guardrails_status,
                ok="L1：維持 preflight 慣例（core/no-exec/no-data）。",
                warn="L2：補跑 guardrails 檢查並修復未達 PASS_EXPECTED 的項目。",
                fail="L3：停止交付，先修復 guardrail fail 再重新驗證。",
                unknown="L2：先刷新 guardrails 區塊與 preflight transcript。",
            ),
        },
    ]

    lines = [
        "📘 每日報告（Single Entry /daily）",
        f"DAILY_REPORT_STATUS: {_daily_norm_status(status)}",
        f"UTC: {generated_utc}",
        "縮寫: "
        f"SSOT({acr_display['SSOT']}) DD({acr_display['DD']}) MDD({acr_display['MDD']}) "
        f"Sharpe({acr_display['Sharpe']}) Trades({acr_display['Trades']}) "
        f"OOS({acr_display['OOS']}) IS({acr_display['IS']}) WF({acr_display['WF']}) "
        f"L1/L2/L3({acr_display['L1/L2/L3']}) TP({acr_display['TP']}) "
        f"SL({acr_display['SL']}) DCA({acr_display['DCA']})",
    ]

    for idx, section in enumerate(sections, start=1):
        lines.extend(
            [
                "",
                f"{idx}) {section['title']}",
                f"狀態: {_daily_norm_status(section['status'])}",
            ]
        )
        source_line = str(section.get("source_line") or "").strip()
        if source_line:
            lines.append(source_line)
        lines.extend(
            [
                f"白話: {section['reason']}",
                f"下一步: {section['next']}",
            ]
        )

    lines.extend(
        [
            "",
            "需要時參考: docs/inventory.md | docs/ops/telegram_operator_manual.md",
            f"RefreshHint: {refresh_hint}",
        ]
    )
    if note:
        lines.append(f"註記: {note}")
    return "\n".join(lines)


def _daily_llm_notes(payload: dict) -> tuple[list[str] | None, str | None]:
    if not callable(call_reasoning_specialist):
        return None, "reasoning_client_unavailable"

    prompt = (
        "你會收到每日報告 SSOT JSON。請輸出 6 句給合作夥伴的短解讀，對應章節："
        "1)SystemHealth 2)DataFreshness 3)Backtest 4)StrategyPool+Leaderboard 5)Governance(Overfit) 6)Guardrails。\n"
        "限制：每句最多 48 字，繁體中文；不可杜撰數字；資料不足請寫「資料不足/UNKNOWN」。\n"
        "請以 ReasoningAnalysis JSON 結構輸出，並把 6 句放到 key_findings。\n\n"
        "SSOT JSON:\n" + json.dumps(payload, ensure_ascii=False)
    )
    system_prompt = (
        "You are a reporting specialist.\n"
        "Return JSON only with ReasoningAnalysis schema.\n"
        "Put exactly six short notes into key_findings.\n"
        "Never invent numbers.\n"
    )

    try:
        analysis = call_reasoning_specialist(prompt, system_prompt=system_prompt, timeout=45)
    except Exception:
        return None, "reasoning_call_exception"
    if not analysis:
        return None, "reasoning_empty"

    problem_lower = str(getattr(analysis, "problem", "")).lower()
    if "call failed" in problem_lower or "extraction failed" in problem_lower:
        return None, "reasoning_failed"

    findings = list(getattr(analysis, "key_findings", []) or [])
    while len(findings) < 6:
        findings.append("資料不足/UNKNOWN")
    return findings[:6], None


def skill_daily_report() -> str:
    payload, load_issue = _daily_load_payload()
    if load_issue:
        return _daily_compose_report(
            payload,
            status="WARN",
            note=f"{load_issue}; run `{payload.get('refresh_hint', _status_refresh_hint())}`",
        )

    base_status = _daily_norm_status(payload.get("ssot_status"))
    notes, llm_issue = _daily_llm_notes(payload)
    if notes:
        return _daily_compose_report(payload, status=base_status, llm_notes=notes)
    return _daily_compose_report(
        payload,
        status=_status_max(base_status, "WARN"),
        note=None,
    )


def _status_short_report_from_health_pack(health_pack: dict) -> str | None:
    if not isinstance(health_pack, dict) or not health_pack:
        return None

    components = health_pack.get("components", {})
    if not isinstance(components, dict):
        return None

    semantics = str(
        health_pack.get("ssot_semantics")
        or "SystemHealth only"
    )
    overall = str(health_pack.get("ssot_status", "UNKNOWN")).upper()
    if overall not in {"OK", "WARN", "FAIL", "UNKNOWN"}:
        overall = "UNKNOWN"

    fresh = components.get("freshness", {})
    cov = components.get("coverage_matrix", {})
    brake = components.get("brake", {})
    regime_monitor = components.get("regime_monitor", {})
    if not isinstance(fresh, dict):
        fresh = {}
    if not isinstance(cov, dict):
        cov = {}
    if not isinstance(brake, dict):
        brake = {}
    if not isinstance(regime_monitor, dict):
        regime_monitor = {}

    fresh_status = str(fresh.get("status", "UNKNOWN")).upper()
    if fresh_status not in {"OK", "WARN", "FAIL", "UNKNOWN"}:
        fresh_status = "UNKNOWN"
    max_age = fresh.get("max_age_h")

    cov_status = _normalize_coverage_status(cov.get("status"))
    if cov_status == "NEEDS_REBASE":
        cov_status = "WARN"
    if cov_status not in {"PASS", "WARN", "FAIL", "UNKNOWN"}:
        cov_status = "UNKNOWN"
    done_count = cov.get("done")
    total_count = cov.get("total")
    max_lag = cov.get("max_lag_h")
    matrix_rebase = cov.get("rebase")

    brake_status = str(brake.get("status", "UNKNOWN")).upper()
    if brake_status not in {"OK", "WARN", "FAIL", "UNKNOWN"}:
        brake_status = "UNKNOWN"

    regime_monitor_status = str(regime_monitor.get("status", "UNKNOWN")).upper()
    if regime_monitor_status not in {"OK", "WARN", "FAIL", "UNKNOWN"}:
        regime_monitor_status = "UNKNOWN"
    regime_monitor_age = regime_monitor.get("age_h")
    regime_ok_h = regime_monitor.get("ok_within_h")
    regime_reason = regime_monitor.get("reason")
    if not isinstance(regime_reason, str) or not regime_reason.strip():
        regime_reason = None
    if regime_reason and len(regime_reason) > 120:
        regime_reason = regime_reason[:117] + "..."
    regime_monitor_line = (
        f"RegimeMonitor: {regime_monitor_status} age_h={_fmt_num(regime_monitor_age)}"
        f" (<= {float(regime_ok_h or REGIME_MONITOR_FRESH_OK_H):.0f}h OK)"
    )
    if regime_reason:
        regime_monitor_line += f" [{regime_reason}]"

    refresh_hint = str(health_pack.get("refresh_hint") or _status_refresh_hint())
    sources_line = _status_ssot_sources_line()

    return "\n".join(
        [
            f"SSOT_STATUS: {overall}",
            f"SSOT_SEMANTICS: {semantics}",
            f"Freshness: {fresh_status} max_age_h={_fmt_num(max_age)}",
            f"CoverageMatrix: {cov_status} {done_count}/{total_count} done | max_lag_h={_fmt_num(max_lag)} | rebase={matrix_rebase}",
            f"Brake: {brake_status}",
            regime_monitor_line,
            f"Action: run `{refresh_hint}` if snapshots look stale",
            sources_line,
        ]
    )


def _status_short_report() -> str:
    health_pack_path = _status_health_pack_path()
    if not health_pack_path.exists():
        return _status_unknown_report(["system_health_latest.json"], [])

    try:
        health_pack = json.loads(health_pack_path.read_text(encoding="utf-8"))
    except Exception:
        return _status_unknown_report([], ["system_health_latest.json"])

    rendered = _status_short_report_from_health_pack(health_pack if isinstance(health_pack, dict) else {})
    if rendered:
        return rendered
    return _status_unknown_report([], ["system_health_latest.json"])


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
    """Read SSOT-only snapshot data for prompts and diagnostics."""
    freshness: dict[str, dict[str, dict[str, object]]] = {}
    freshness_snap = _load_json(REPO / "data/state/freshness_table.json", {})
    freshness_rows = freshness_snap.get("rows", []) if isinstance(freshness_snap, dict) else []
    if isinstance(freshness_rows, list):
        for row in freshness_rows:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol") or "").strip()
            tf = str(row.get("tf") or "").strip()
            if not sym or not tf:
                continue
            if sym not in freshness:
                freshness[sym] = {}
            freshness[sym][tf] = {
                "age_hours": row.get("age_h"),
                "status": str(row.get("status", "UNKNOWN")).upper(),
                "reason": row.get("reason"),
            }

    regime_raw = _load_json(REPO / "data/state/regime_monitor_latest.json", {})
    regime = regime_raw if isinstance(regime_raw, dict) else {}
    regime_status = str(
        regime.get("status")
        or regime.get("overall")
        or regime.get("overall_status")
        or "UNKNOWN"
    ).upper()
    if regime_status not in {"OK", "WARN", "FAIL", "UNKNOWN"}:
        regime_status = "UNKNOWN"
    if "status" not in regime:
        regime["status"] = regime_status
    if "overall" not in regime and regime_status != "UNKNOWN":
        regime["overall"] = regime_status

    return {
        "status_report": _status_short_report(),
        "freshness": freshness,
        "regime_monitor": regime,
        "pending_alerts": _count_pending_alerts(),
        "refresh_hint": _status_refresh_hint(),
    }


def _snapshot_text() -> str:
    """Build a compact SSOT-only summary for LLM system prompts."""
    snap = _collect_snapshot()
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    status_report = str(snap.get("status_report") or _status_unknown_report([], []))
    refresh_hint = str(snap.get("refresh_hint") or _status_refresh_hint())

    parts = [
        f"[系統快照 {now}]",
        status_report,
        f"RefreshHint: Run `{refresh_hint}` when SSOT snapshots are missing or stale.",
    ]

    pending_alerts = snap.get("pending_alerts")
    if isinstance(pending_alerts, int) and pending_alerts > 0:
        parts.append(f"⚠️ 待處理排程告警: {pending_alerts} 筆")

    return "\n".join(parts)


# ────────────────────── skills (read-only) ──────────────────────
def skill_status_overview(include_sources: bool = False) -> str:
    # Status-class output must stay SSOT-only; reuse the /status formatter.
    report = _status_short_report()
    if include_sources:
        return report
    return "\n".join(
        line for line in report.splitlines() if not line.startswith("Sources:")
    )


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


def skill_incident_timeline_builder(
    start: str,
    end: str,
    env: str,
    keywords: str = "",
    services: str = "",
) -> str:
    """Read-only incident timeline from SSOT snapshots only."""
    payload = build_incident_timeline(
        REPO,
        start=start,
        end=end,
        env=env,
        keywords=keywords,
        services=services,
    )
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def skill_system_health_morning_brief(args: dict) -> str:
    env = str(args.get("env", "prod"))
    include_details = bool(args.get("include_details", False))
    try:
        from _local.telegram_cp.skills.system_health_morning_brief import get_morning_brief
    except ImportError:
        from system_health_morning_brief import get_morning_brief
    payload = get_morning_brief(REPO, env, include_details)
    return payload["markdown"]


def skill_config_drift_auditor(args: dict) -> str:
    baseline_ref = str(args.get("baseline_ref", ""))
    paths = str(args.get("paths", ""))
    try:
        from _local.telegram_cp.skills.config_drift_auditor import audit_config_drift
    except ImportError:
        from config_drift_auditor import audit_config_drift
    payload = audit_config_drift(REPO, baseline_ref, paths)
    return payload["markdown"]


def skill_data_freshness_watchdog_report(args: dict) -> str:
    env = str(args.get("env", "prod"))
    try:
        from _local.telegram_cp.skills.data_freshness_watchdog_report import get_freshness_report
    except ImportError:
        from data_freshness_watchdog_report import get_freshness_report
    payload = get_freshness_report(REPO, env)
    return payload["markdown"]


def skill_execution_quality_report_readonly(args: dict) -> str:
    env = str(args.get("env", "prod"))
    try:
        from _local.telegram_cp.skills.execution_quality_report_readonly import get_execution_quality_report
    except ImportError:
        from execution_quality_report_readonly import get_execution_quality_report
    payload = get_execution_quality_report(REPO, env)
    return payload["markdown"]


def skill_backtest_reproducibility_audit(args: dict) -> dict:
    backtest_id = str(args.get("backtest_id", ""))
    baseline_sha = str(args.get("baseline_sha", ""))
    try:
        from _local.telegram_cp.skills.backtest_reproducibility_audit import audit_backtest_reproducibility
    except ImportError:
        from backtest_reproducibility_audit import audit_backtest_reproducibility
    payload = audit_backtest_reproducibility(REPO, backtest_id, baseline_sha)
    return payload


def skill_factor_health_and_drift_report(args: dict) -> dict:
    factor_id = str(args.get("factor_id", ""))
    try:
        from _local.telegram_cp.skills.factor_health_and_drift_report import get_factor_health_report
    except ImportError:
        from factor_health_and_drift_report import get_factor_health_report
    payload = get_factor_health_report(REPO, factor_id)
    return payload


def skill_strategy_regime_sensitivity_report(args: dict) -> dict:
    strategy_id = str(args.get("strategy_id", ""))
    try:
        from _local.telegram_cp.skills.strategy_regime_sensitivity_report import get_strategy_sensitivity_report
    except ImportError:
        from strategy_regime_sensitivity_report import get_strategy_sensitivity_report
    payload = get_strategy_sensitivity_report(REPO, strategy_id)
    return payload


def skill_rag_search(args: dict) -> dict:
    try:
        from _local.telegram_cp.skills.rag_search import run_rag_search
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "skills"))
        from rag_search import run_rag_search
    payload = run_rag_search(REPO, args)
    return payload


def skill_signal_leakage_audit(args: dict) -> str:
    artifact_path = str(args.get("artifact_path", "research/audit/tests/fixtures/clean.json"))
    max_lookahead_ms = int(args.get("max_lookahead_ms", 0))
    try:
        from research.audit.lookahead import audit_from_artifact
    except Exception as exc:
        payload = {
            "summary": "audit_loader_error",
            "status": "UNKNOWN",
            "report_only": True,
            "issues": [
                {
                    "type": "import_error",
                    "severity": "HIGH",
                    "description": "Failed to import research.audit.lookahead",
                    "evidence": str(exc),
                }
            ],
            "refresh_hint": "Ensure research audit module is available",
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    payload = audit_from_artifact(REPO, artifact_path=artifact_path, max_allowed_lookahead_ms=max_lookahead_ms)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

def skill_run_integrity_report(args: dict) -> dict:
    try:
        from _local.telegram_cp.skills.run_integrity_report import generate_run_integrity_report
    except ImportError:
        from run_integrity_report import generate_run_integrity_report
    return generate_run_integrity_report(REPO)

def skill_worker_acceptance_check(args: dict) -> dict:
    try:
        from _local.telegram_cp.skills.worker_acceptance_check import generate_worker_acceptance_check
    except ImportError:
        from worker_acceptance_check import generate_worker_acceptance_check
    return generate_worker_acceptance_check(REPO)

SKILL_IMPL = {
    "run_integrity_report": skill_run_integrity_report,
    "worker_acceptance_check": skill_worker_acceptance_check,
    "backtest_reproducibility_audit": skill_backtest_reproducibility_audit,
    "factor_health_and_drift_report": skill_factor_health_and_drift_report,
    "strategy_regime_sensitivity_report": skill_strategy_regime_sensitivity_report,

    "execution_quality_report_readonly": skill_execution_quality_report_readonly,
    "data_freshness_watchdog_report": skill_data_freshness_watchdog_report,
    "config_drift_auditor": skill_config_drift_auditor,
    "system_health_morning_brief": skill_system_health_morning_brief,
    "status_overview": lambda args: skill_status_overview(bool(args.get("include_sources", False))),
    "logs_tail_hint": lambda args: skill_logs_tail_hint(int(args.get("lines", 60))),
    "freshness_detail": lambda args: skill_freshness_detail(),
    "ml_status": lambda args: skill_ml_status(),
    "regime_status": lambda args: skill_regime_status(),
    "brake_status": lambda args: skill_brake_status(),
    "signal_leakage_audit": lambda args: skill_signal_leakage_audit(args),
    "signal_leakage_and_lookahead_audit": lambda args: skill_signal_leakage_audit(args),
    "incident_timeline_builder": lambda args: skill_incident_timeline_builder(
        str(args.get("start", "")),
        str(args.get("end", "")),
        str(args.get("env", "prod")),
        str(args.get("keywords", "")),
        str(args.get("services", "")),
    ),
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
        txt = (
            f"☀️ 洪老裴早安！今日快照（{today_str}）："
            f"\n{_snapshot_text()[:800]}"
            "\n（LLM 離線，以上為 SSOT 快照）"
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


def _build_ollama_system_prompt(model_name: str) -> str:
    existing_system = _build_system_prompt()
    if not TG_PROMPT_PACK_ENABLED or build_prompt_pack_system_prompt is None:
        return existing_system
    try:
        pack_system = build_prompt_pack_system_prompt(model_name)
    except Exception as exc:
        logger.warning("Prompt pack unavailable; falling back to existing system prompt (%s)", type(exc).__name__)
        return existing_system
    if not pack_system.strip():
        logger.warning("Prompt pack returned empty content; falling back to existing system prompt")
        return existing_system
    return pack_system.strip() + "\n\n" + existing_system


def _llm_chat(chat_id: int, user_text: str, history: list[dict]) -> tuple[str, str | None]:
    """Call Ollama /api/chat with system prompt + conversation history + new user message."""
    system_prompt = _build_ollama_system_prompt(OLLAMA_MODEL)

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
def _handle_command(chat_id: int, text: str) -> str:
    cmd = _cmd_base(text)

    if cmd == "/start":
        return (
            "嗨 👋 我是 HONGSTR 中樞管家。\n"
            "直接跟我聊就好，問什麼我都會盡量用白話回答你。\n"
            "我是 read-only 助手 — 只查看、判讀，不直接動系統。\n\n"
            "快捷指令：/status /daily /brake /regime /freshness"
        )

    if cmd == "/ping":
        return "pong ✅"

    if cmd == "/help":
        return (
            "直接打字問我就好，不需要特別格式 😊\n\n"
            "📊 監控指令（read-only）：\n"
            "• /status — 系統瓶頸摘要\n"
            "• /daily — 每日 SSOT 報告（固定模板 + LLM 潤飾失敗自動降級）\n"
            "• /brake — 煞車健康檢查 (Artifacts & Freshness)\n"
            "• /regime — 市場機制監控（舒適圈 OK/WARN/FAIL）\n"
            "• /freshness — 資料新鮮度（3幣×3時框表格）"
        )

    if cmd == "/status":
        return _status_short_report()

    if cmd == "/daily":
        return skill_daily_report()

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


    if cmd == "/consult":
        return "__DELEGATE_TO_ROUTER__"

    return "不認識這個指令，目前僅支援：/status, /daily, /brake, /regime, /freshness"


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
