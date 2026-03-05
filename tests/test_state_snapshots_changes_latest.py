import importlib.util
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/state_snapshots.py"


def _load_state_snapshots_module():
    scripts_dir = (REPO / "scripts").resolve()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location("state_snapshots_changes_latest_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_write_changes_latest_alias_from_source(tmp_path: Path):
    mod = _load_state_snapshots_module()
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    source_path = state_dir / "data_catalog_changes_latest.json"
    source_payload = {
        "ts_utc": "2026-03-05T00:00:00Z",
        "prev_ts_utc": "2026-03-04T00:00:00Z",
        "added_datasets": [{"dataset_id": "btc_1m", "summary": "dataset added"}],
        "removed_datasets": [],
        "updated_datasets": [],
    }
    source_path.write_text(json.dumps(source_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    original_state_dir = mod.STATE_DIR
    try:
        mod.STATE_DIR = state_dir
        alias_payload = mod._write_changes_latest_alias("2026-03-05T01:02:03Z", source_path)
    finally:
        mod.STATE_DIR = original_state_dir

    alias_path = state_dir / "changes_latest.json"
    assert alias_path.exists()
    alias_json = json.loads(alias_path.read_text(encoding="utf-8"))
    assert alias_json["ts_utc"] == "2026-03-05T00:00:00Z"
    assert alias_json["status"] == "OK"
    assert alias_json["reason"] == "alias_data_catalog_changes_latest"
    assert isinstance(alias_json["changes"], list)
    assert alias_json["source"]["path"].endswith("data_catalog_changes_latest.json")
    assert alias_json["source"]["status"] == "present"
    assert alias_payload == alias_json


def test_write_changes_latest_alias_missing_source_degrades_warn(tmp_path: Path):
    mod = _load_state_snapshots_module()
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    missing_source = state_dir / "data_catalog_changes_latest.json"

    original_state_dir = mod.STATE_DIR
    try:
        mod.STATE_DIR = state_dir
        mod._write_changes_latest_alias("2026-03-05T01:02:03Z", missing_source)
    finally:
        mod.STATE_DIR = original_state_dir

    alias_path = state_dir / "changes_latest.json"
    assert alias_path.exists()
    alias_json = json.loads(alias_path.read_text(encoding="utf-8"))
    assert alias_json["ts_utc"] == "2026-03-05T01:02:03Z"
    assert alias_json["status"] == "WARN"
    assert alias_json["reason"] == "missing_source"
    assert alias_json["changes"] == []
    assert alias_json["source"]["status"] == "missing"


def test_main_writes_changes_latest_json(tmp_path: Path, monkeypatch):
    mod = _load_state_snapshots_module()
    monkeypatch.chdir(tmp_path)

    mod.main()

    changes_path = tmp_path / "data" / "state" / "changes_latest.json"
    assert changes_path.exists()
    payload = json.loads(changes_path.read_text(encoding="utf-8"))
    assert isinstance(payload.get("ts_utc"), str)
    assert payload.get("status") in {"OK", "WARN", "FAIL", "UNKNOWN"}
    assert isinstance(payload.get("changes"), list)
