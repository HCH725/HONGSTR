import json
import importlib.util
from pathlib import Path

from _local.telegram_cp.skills.system_health_morning_brief import build_system_health_morning_brief


FIXTURES = Path("/Users/hong/Projects/HONGSTR/_local/telegram_cp/tests/fixtures/system_health_brief")


def _load_server():
    p = Path("/Users/hong/Projects/HONGSTR/_local/telegram_cp/tg_cp_server.py")
    spec = importlib.util.spec_from_file_location("tg_cp_server_skill_testmod", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_morning_brief_from_health_pack_schema():
    repo = FIXTURES / "with_health_pack"
    result = build_system_health_morning_brief(repo)

    assert set(result.keys()) == {"summary", "score", "findings", "evidence", "actions_suggested"}
    assert result["summary"]["status"] == "OK"
    assert result["summary"]["report_only"] is True
    assert isinstance(result["score"], dict)
    assert set(result["score"].keys()) == {"health", "data", "latency"}
    assert isinstance(result["findings"], list)
    assert isinstance(result["evidence"], list)
    assert isinstance(result["actions_suggested"], list)
    assert any("data/state/" in item for item in result["evidence"])


def test_morning_brief_ssot_fallback_components_only():
    repo = FIXTURES / "fallback_components"
    result = build_system_health_morning_brief(repo)

    assert result["summary"]["report_only"] is True
    assert result["summary"]["status"] in {"OK", "WARN", "UNKNOWN"}
    assert any("fallback_mode" in item for item in result["findings"])
    assert not any("derived" in item.lower() for item in result["evidence"])


def test_morning_brief_missing_inputs_unknown_with_refresh_hint():
    repo = FIXTURES / "missing_inputs"
    result = build_system_health_morning_brief(repo)

    assert result["summary"]["status"] == "UNKNOWN"
    assert "refresh_state.sh" in str(result["summary"]["refresh_hint"])
    assert result["summary"]["report_only"] is True


def test_run_skill_from_registry(monkeypatch, tmp_path):
    s = _load_server()
    monkeypatch.setattr(s, "REPO", FIXTURES / "with_health_pack")
    monkeypatch.setattr(s, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(s, "OFFSET_PATH", tmp_path / "state" / "offset.json")
    monkeypatch.setattr(s, "SESSION_PATH", tmp_path / "state" / "session_state.json")
    monkeypatch.setattr(s, "OPS_MEM", tmp_path / "state" / "ops_memory.jsonl")
    monkeypatch.setattr(s, "USER_MEM", tmp_path / "state" / "user_memory.jsonl")
    monkeypatch.setattr(s, "RUNTIME_LOG", tmp_path / "state" / "runtime.log")
    monkeypatch.setattr(s, "ALERTS_PENDING", tmp_path / "state" / "alerts_pending.jsonl")
    monkeypatch.setattr(s, "FOLLOWUP_QUEUE", tmp_path / "state" / "followup_queue.jsonl")
    s._ensure_state()

    out, ok = s._handle_run("/run system_health_morning_brief")
    assert ok is True
    obj = json.loads(out)
    assert obj["summary"]["report_only"] is True
    assert set(obj.keys()) == {"summary", "score", "findings", "evidence", "actions_suggested"}
