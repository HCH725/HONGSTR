import importlib.util
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/futures_metrics_lib.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("futures_metrics_manifest_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_futures_manifest_schema_shape():
    mod = _load_module()
    manifest = mod.build_futures_metrics_manifest(Path("/tmp/not-a-repo"))

    assert set(manifest.keys()) == {
        "dataset_id",
        "schema_version",
        "producer",
        "cadence",
        "path_patterns",
        "symbols",
        "metrics",
        "periods",
        "sources",
        "provenance",
        "notes",
    }
    assert manifest["dataset_id"] == "futures_metrics"
    assert manifest["schema_version"] == "v1"
    assert isinstance(manifest["producer"], str) and manifest["producer"]
    assert isinstance(manifest["cadence"], str) and manifest["cadence"]
    assert set(manifest["path_patterns"].keys()) == {"root", "template"}
    assert all(isinstance(item, str) for item in manifest["symbols"])
    assert all(isinstance(item, str) for item in manifest["metrics"])
    assert all(isinstance(item, str) for item in manifest["periods"])
    assert isinstance(manifest["sources"], list) and manifest["sources"]
    assert set(manifest["sources"][0].keys()) == {"name", "endpoints"}
    assert all(isinstance(item, str) for item in manifest["sources"][0]["endpoints"])
    assert set(manifest["provenance"].keys()) == {"generated_utc", "code_ref"}
    assert isinstance(manifest["provenance"]["generated_utc"], str) and manifest["provenance"]["generated_utc"]
    assert isinstance(manifest["provenance"]["code_ref"], str) and manifest["provenance"]["code_ref"]
    assert isinstance(manifest["notes"], str)
