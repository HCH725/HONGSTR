import json
from pathlib import Path

from hongstr.control_plane import runner


class _BadLLM:
    def generate(self, decision_prompt: str) -> str:
        return "not-json"


def test_runner_invalid_llm_json_writes_fail_artifact(tmp_path, monkeypatch):
    event_file = tmp_path / "latest_event.json"
    event_file.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "event_id": "evt_bad_json",
                "created_at_utc": "2026-01-01T00:00:00+00:00",
                "source": "test",
                "payload": {"x": 1},
            }
        ),
        encoding="utf-8",
    )

    out_json = tmp_path / "control_plane_latest.json"
    out_md = tmp_path / "control_plane_latest.md"

    monkeypatch.setattr(runner, "build_llm_from_env", lambda: (_BadLLM(), "qwen"))

    rc = runner.run_control_plane(event_file, out_json, out_md)
    assert rc == 0
    assert out_json.exists()

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["status"] == "FAIL"
    assert "parsing/validation failed" in data["summary"].lower()


def test_runner_missing_event_never_crashes(tmp_path):
    out_json = tmp_path / "control_plane_latest.json"
    out_md = tmp_path / "control_plane_latest.md"
    rc = runner.run_control_plane(tmp_path / "missing.json", out_json, out_md)
    assert rc == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["status"] == "FAIL"
