from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_status_snapshot_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "status_snapshot.py"
    spec = importlib.util.spec_from_file_location("status_snapshot_script", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collect_status_snapshot_with_missing_files(tmp_path):
    module = _load_status_snapshot_module()
    snapshot = module.collect_status_snapshot(tmp_path)

    assert isinstance(snapshot, dict)
    assert "time_utc" in snapshot
    assert "git" in snapshot
    assert "services" in snapshot
    assert "coverage" in snapshot
    assert "runs" in snapshot
    assert "gate" in snapshot
    assert "telemetry" in snapshot
    assert "warnings" in snapshot

    assert snapshot["runs"]["total"] == 0
    assert snapshot["runs"]["latest_run_dir"] is None
    assert snapshot["coverage"]["overall_status"] == "FAIL"
    assert isinstance(snapshot["warnings"], list)
