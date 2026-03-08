import importlib.util
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = (REPO / "scripts").resolve()
BOUNDARY_SCRIPT = REPO / "scripts" / "check_state_writer_boundary.py"
INVENTORY_SCRIPT = REPO / "scripts" / "state_writer_inventory.py"
REFRESH_STATE_SCRIPT = REPO / "scripts" / "refresh_state.sh"


def _load_module(name: str, path: Path):
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_writer_inventory_covers_every_state_snapshots_output():
    mod = _load_module("state_writer_boundary_testmod", BOUNDARY_SCRIPT)
    missing, extra = mod.inventory_coverage_issues()
    assert missing == []
    assert extra == []


def test_writer_inventory_has_complete_single_writer_mapping():
    mod = _load_module("state_writer_inventory_testmod", INVENTORY_SCRIPT)
    paths = set()
    for entry in mod.CANONICAL_STATE_WRITER_INVENTORY:
        assert entry["designated_writer"] == mod.DESIGNATED_WRITER
        assert entry["designated_orchestrator"] == mod.DESIGNATED_ORCHESTRATOR
        assert entry["owner_plane"] in mod.ALLOWED_OWNER_PLANES
        assert entry["owner_role"]
        assert entry["publication_tier"]
        assert entry["status"] == "active"
        assert entry["update_cadence"]
        assert entry["responsibility"]
        assert entry["degrade_hint"]
        assert entry["kill_hint"]
        assert entry["sop_hint"] == "bash scripts/refresh_state.sh"
        assert entry["canonical_path"].startswith("data/state/")
        assert entry["canonical_path"] not in paths
        paths.add(entry["canonical_path"])


def test_boundary_check_passes_and_refresh_state_stays_orchestrator_only():
    boundary = _load_module("state_writer_boundary_orchestrator_testmod", BOUNDARY_SCRIPT)
    assert boundary.inventory_shape_issues() == []
    assert boundary.scan() == []

    refresh_text = REFRESH_STATE_SCRIPT.read_text(encoding="utf-8")
    assert "scripts/check_state_writer_boundary.py --strict" in refresh_text
    assert "scripts/state_snapshots.py" in refresh_text
    for line in refresh_text.splitlines():
        if not boundary.WRITE_HINT_RE.search(line):
            continue
        assert not any(name in line for name in boundary.CANONICAL_FILES), line
