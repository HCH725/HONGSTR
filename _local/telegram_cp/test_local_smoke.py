"""Smoke tests for the LLM-first tg_cp_server.

These tests validate:
  • guardrail still blocks dangerous requests
  • policy + skills contract unchanged
  • /commands work without LLM
  • conversation history accumulates
  • system prompt includes snapshot + memories
  • secrets are redacted
"""
import json
import importlib.util
from pathlib import Path


def _sandbox_state(monkeypatch, tmp_path, s):
    monkeypatch.setattr(s, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(s, "OFFSET_PATH", tmp_path / "state" / "offset.json")
    monkeypatch.setattr(s, "SESSION_PATH", tmp_path / "state" / "session_state.json")
    monkeypatch.setattr(s, "OPS_MEM", tmp_path / "state" / "ops_memory.jsonl")
    monkeypatch.setattr(s, "USER_MEM", tmp_path / "state" / "user_memory.jsonl")
    monkeypatch.setattr(s, "RUNTIME_LOG", tmp_path / "state" / "runtime.log")
    monkeypatch.setattr(s, "ALERTS_PENDING", tmp_path / "state" / "alerts_pending.jsonl")
    monkeypatch.setattr(s, "FOLLOWUP_QUEUE", tmp_path / "state" / "followup_queue.jsonl")
    s._ensure_state()


def _load_server():
    p = Path("/Users/hong/Projects/HONGSTR/_local/telegram_cp/tg_cp_server.py")
    spec = importlib.util.spec_from_file_location("tg_cp_server_testmod", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


# ── guardrail ──

def test_guardrail_blocks_action_request(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp, route = s.build_chat_reply(1, "幫我重啟 dashboard", use_llm=False)
    assert route == "REFUSE"
    assert "read-only" in resp or "不能" in resp
    # should include safe SOP
    assert "healthcheck" in resp or "SOP" in resp or "手動" in resp


def test_guardrail_blocks_trade_request(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp, route = s.build_chat_reply(2, "幫我買進 BTC", use_llm=False)
    assert route == "REFUSE"
    assert "不能" in resp or "read-only" in resp


# ── policy + skills contract ──

def test_policy_and_skills_contract():
    policy = json.loads(Path("/Users/hong/Projects/HONGSTR/_local/telegram_cp/policy.json").read_text(encoding="utf-8"))
    skills = json.loads(Path("/Users/hong/Projects/HONGSTR/_local/telegram_cp/skills_registry.json").read_text(encoding="utf-8"))["skills"]

    assert policy["mode"] == "read_only"
    assert policy["allowed_actions"] == []
    names = [s["name"] for s in skills]
    assert names == ["status_overview", "logs_tail_hint"]


# ── commands work without LLM ──

def test_start_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(10, "/start")
    assert "中樞管家" in resp
    assert "不支援" not in resp
    assert "/status" in resp and "/help" in resp

    resp2 = s._handle_command(10, "/start@HONGSTR_bot")
    assert "中樞管家" in resp2


def test_help_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(20, "/help")
    assert "/status" in resp
    assert "/skills" in resp


def test_status_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(30, "/status")
    # should have snapshot content
    assert "BTCUSDT" in resp or "快照" in resp


def test_ping_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(40, "/ping")
    assert resp == "pong ✅"


def test_skills_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(50, "/skills")
    assert "status_overview" in resp
    assert "logs_tail_hint" in resp


def test_unknown_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(60, "/foobar")
    assert "/help" in resp


# ── conversation history ──

def test_history_accumulates(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    state = s._load_session_state()
    assert s._get_history(state, 100) == []

    s._append_history(state, 100, "user", "hello")
    s._append_history(state, 100, "assistant", "hi there")
    s._save_session_state(state)

    state2 = s._load_session_state()
    history = s._get_history(state2, 100)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_history_trims_to_max(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "HISTORY_MAX_TURNS", 3)

    state = s._load_session_state()
    for i in range(10):
        s._append_history(state, 200, "user", f"msg-{i}")
        s._append_history(state, 200, "assistant", f"reply-{i}")
    s._save_session_state(state)

    state2 = s._load_session_state()
    history = s._get_history(state2, 200)
    assert len(history) <= 6  # 3 turns * 2 messages


# ── system prompt ──

def test_system_prompt_includes_snapshot(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    prompt = s._build_system_prompt()
    assert "系統快照" in prompt
    assert "read-only" in prompt or "唯讀" in prompt or "硬圍欄" in prompt


def test_system_prompt_includes_user_memories(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    # write a memory
    s._write_user_memory(300, "以後叫我洪老爺")

    prompt = s._build_system_prompt()
    assert "洪老爺" in prompt


# ── secret redaction ──

def test_reply_does_not_leak_token():
    from _local.telegram_cp.guardrail import redact_secrets
    text = "token is bot123456:ABCDefGHIjklmnOP_qrstuvwxyz"
    cleaned = redact_secrets(text)
    assert "bot123456" not in cleaned
    assert "<REDACTED>" in cleaned


# ── LLM offline fallback ──

def test_llm_offline_returns_fallback(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp, route = s.build_chat_reply(400, "你好", use_llm=False)
    assert route == "FALLBACK"
    assert "LLM" in resp or "/status" in resp or "/help" in resp


# ── remember command ──

def test_remember_and_memories(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(500, "/remember 以後叫我洪老爺")
    assert "記" in resp

    resp2 = s._handle_command(500, "/memories")
    assert "洪老爺" in resp2


# ── deferred followup queue ──

def test_extract_followup_tag_basic():
    from _local.telegram_cp.tg_cp_server import _extract_followup_tag
    text = "好的，我幫你查，等等回報你。\n[FOLLOWUP:5:ETL 狀態和資料新鮮度]"
    minutes, topic, cleaned = _extract_followup_tag(text)
    assert minutes == 5
    assert "ETL" in topic
    assert "[FOLLOWUP" not in cleaned


def test_extract_followup_tag_none():
    from _local.telegram_cp.tg_cp_server import _extract_followup_tag
    text = "系統目前看起來正常。"
    minutes, topic, cleaned = _extract_followup_tag(text)
    assert minutes is None
    assert topic is None
    assert cleaned == text


def test_extract_followup_tag_spaced():
    from _local.telegram_cp.tg_cp_server import _extract_followup_tag
    text = "馬上為您處理。\n[ FOLLOWUP : 2 : ETL 狀態和資料新鮮度 ]"
    minutes, topic, cleaned = _extract_followup_tag(text)
    assert minutes == 2
    assert "ETL" in topic
    assert "[ FOLLOWUP" not in cleaned


def test_extract_followup_tag_clamp():
    from _local.telegram_cp.tg_cp_server import _extract_followup_tag
    # 999 minutes should be clamped to FOLLOWUP_MAX_DELAY_MIN (default 60)
    text = "等等告訴你。\n[FOLLOWUP:999:CPU 狀態]"
    minutes, topic, cleaned = _extract_followup_tag(text)
    assert minutes is not None
    assert minutes <= 60


def test_enqueue_and_load_followup(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "FOLLOWUP_ENABLED", True)

    s._enqueue_followup(100, 5, "ETL 狀態", "ETL 好了嗎")

    due = s._load_due_followups()
    assert len(due) == 0  # not due yet (due_at = now + 5 min)

    # Manually back-date it
    import json
    lines = s.FOLLOWUP_QUEUE.read_text().splitlines()
    records = [json.loads(l) for l in lines if l.strip()]
    records[0]["due_at"] = 1  # epoch 1 = far in the past
    s.FOLLOWUP_QUEUE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
    )

    due = s._load_due_followups()
    assert len(due) == 1
    assert due[0]["topic"] == "ETL 狀態"


def test_mark_followups_done(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "FOLLOWUP_ENABLED", True)

    s._enqueue_followup(200, 1, "測試主題", "msg")
    import json
    lines = s.FOLLOWUP_QUEUE.read_text().splitlines()
    fid = json.loads(lines[0])["id"]

    s._mark_followups_done([fid])

    lines2 = s.FOLLOWUP_QUEUE.read_text().splitlines()
    assert json.loads(lines2[0])["done"] is True


def test_build_chat_reply_enqueues_followup(monkeypatch, tmp_path):
    """build_chat_reply strips FOLLOWUP tag and enqueues the task."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "FOLLOWUP_ENABLED", True)

    # Mock LLM to return a response with a FOLLOWUP tag
    def fake_llm(chat_id, user_text, history):
        return "好的，等一下回報你。\n[FOLLOWUP:3:ETL 資料新鮮度]", None
    monkeypatch.setattr(s, "_llm_chat", fake_llm)

    resp, route = s.build_chat_reply(600, "ETL 好了嗎")
    assert route == "LLM"
    assert "[FOLLOWUP" not in resp  # tag stripped from visible reply
    assert "好的" in resp

    # Queue should have one entry
    import json
    lines = s.FOLLOWUP_QUEUE.read_text().splitlines()
    assert len(lines) == 1
    task = json.loads(lines[0])
    assert task["topic"] == "ETL 資料新鮮度"
    assert task["done"] is False
    assert task["chat_id"] == 600
    assert task["chat_id"] == 600


# ── freshness ──

def test_evaluate_freshness_boundaries():
    from _local.telegram_cp.tg_cp_server import _evaluate_freshness
    
    # OK: <= 12h
    assert _evaluate_freshness(0.0)[0] == "OK"
    assert _evaluate_freshness(12.0)[0] == "OK"
    
    # WARN: 12 < age <= 48
    assert _evaluate_freshness(12.1)[0] == "WARN"
    assert "exceeds 12h" in _evaluate_freshness(12.1)[1]
    assert _evaluate_freshness(48.0)[0] == "WARN"
    
    # FAIL: > 48
    assert _evaluate_freshness(48.1)[0] == "FAIL"
    assert "exceeds 48h" in _evaluate_freshness(48.1)[1]
    
    # None: WARN (missing file)
    assert _evaluate_freshness(None)[0] == "WARN"
    assert "missing" in _evaluate_freshness(None)[1]


def test_snapshot_text_freshness_logic(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    # Case A: All OK
    fake_snap = {
        "dashboard_ok": True,
        "freshness": {
            "BTCUSDT": {
                "1m": {"age_hours": 5.4, "status": "OK"},
                "1h": {"age_hours": 6.7, "status": "OK"},
                "4h": {"age_hours": 8.2, "status": "OK"},
            },
            "ETHUSDT": {
                "1m": {"age_hours": 5.9, "status": "OK"},
                "1h": {"age_hours": 6.5, "status": "OK"},
                "4h": {"age_hours": 8.0, "status": "OK"},
            },
            "BNBUSDT": {
                "1m": {"age_hours": 5.7, "status": "OK"},
                "1h": {"age_hours": 6.3, "status": "OK"},
                "4h": {"age_hours": 7.8, "status": "OK"},
            }
        },
        "log_ages": {}, "cp_status": "OK", "cp_summary": "", "cp_age_hours": 0.1,
        "overall_gate": "PASS", "top_action": "", "etl_fail": False, "etl_ok": True, "pending_alerts": 0
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    
    text = s._snapshot_text()
    assert "良好 (皆在 12h 內)" in text
    assert "WARN" not in text
    assert "延遲" not in text
    assert "落後" not in text  # "資料落後" was removed for overall_ok case in my implementation
    assert "BTCUSDT: 1m:5.4h(OK) / 1h:6.7h(OK) / 4h:8.2h(OK)" in text

    # Case B: One WARN
    fake_snap["freshness"]["BTCUSDT"]["4h"] = {"age_hours": 20.0, "status": "WARN"}
    text = s._snapshot_text()
    assert "⚠️ 延遲 (部分超過 12h)" in text
    assert "BTCUSDT: 1m:5.4h(OK) / 1h:6.7h(OK) / 4h:20.0h(WARN)" in text

    # Case C: One FAIL
    fake_snap["freshness"]["ETHUSDT"]["1m"] = {"age_hours": 60.0, "status": "FAIL"}
    text = s._snapshot_text()
    assert "❌ 嚴重落後 (部分超過 48h)" in text
    assert "ETHUSDT: 1m:60.0h(FAIL)" in text
