import importlib.util
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/state_atomic/okx_bitfinex_public_manifest.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("okx_bfx_manifest_written_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _assert_manifest_shape(payload: dict):
    assert set(payload.keys()) == {
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
    assert payload["schema_version"] == "v1"
    assert isinstance(payload["dataset_id"], str) and payload["dataset_id"]
    assert isinstance(payload["producer"], str) and payload["producer"]
    assert isinstance(payload["cadence"], str) and payload["cadence"]
    assert set(payload["path_patterns"].keys()) == {"root", "template"}
    assert isinstance(payload["symbols"], list)
    assert isinstance(payload["metrics"], list)
    assert isinstance(payload["periods"], list)
    assert isinstance(payload["sources"], list) and payload["sources"]
    assert set(payload["provenance"].keys()) == {"generated_utc", "code_ref"}
    assert isinstance(payload["notes"], str)


def test_write_manifests_creates_expected_files(tmp_path: Path):
    mod = _load_module()

    okx_path = mod.write_okx_manifest(tmp_path, ["BTC", "ETH", "BNB"])
    bitfinex_path = mod.write_bitfinex_manifest(tmp_path)

    assert okx_path.exists()
    assert bitfinex_path.exists()

    okx_payload = json.loads(okx_path.read_text(encoding="utf-8"))
    bitfinex_payload = json.loads(bitfinex_path.read_text(encoding="utf-8"))

    _assert_manifest_shape(okx_payload)
    _assert_manifest_shape(bitfinex_payload)
    assert okx_payload["dataset_id"] == "okx_public_v1"
    assert bitfinex_payload["dataset_id"] == "bitfinex_public_v1"
