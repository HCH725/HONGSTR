from pathlib import Path


def test_gate_prefers_full_artifact():
    gate = Path("scripts/gate_all.sh").read_text(encoding="utf-8")
    assert "WF_PREFER_FULL" in gate
    assert "find_latest_full_walkforward_json_for_sha" in gate
    assert "emit_latest_pointer_from_json" in gate

    rpt = Path("scripts/report_walkforward.py").read_text(encoding="utf-8")
    assert "--from-json" in rpt or "from_json" in rpt
    assert "--emit-latest-pointer" in rpt or "emit_latest" in rpt
