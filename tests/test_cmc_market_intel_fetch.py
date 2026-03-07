import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "cmc_market_intel_fetch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cmc_market_intel_fetch", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _patch_output_paths(monkeypatch, cmc, tmp_path):
    monkeypatch.setattr(cmc, "ATOMIC_COVERAGE_PATH", tmp_path / "cmc_market_intel_coverage.json")
    monkeypatch.setattr(cmc, "MANIFEST_PATH", tmp_path / "cmc_market_intel_v1.json")
    monkeypatch.setattr(cmc, "DERIVED_ROOT_NARRATIVES", tmp_path / "narratives")
    monkeypatch.setattr(cmc, "DERIVED_ROOT_MACRO", tmp_path / "macro_events")
    monkeypatch.setattr(cmc, "write_manifest", lambda ts_utc: None)


def test_missing_key_keeps_fail_reason(monkeypatch, tmp_path):
    cmc = _load_module()
    _patch_output_paths(monkeypatch, cmc, tmp_path)
    monkeypatch.setattr(cmc, "_load_api_key", lambda: None)

    assert cmc.main() == 0

    coverage = json.loads((tmp_path / "cmc_market_intel_coverage.json").read_text())
    assert coverage["status"] == "FAIL"
    assert coverage["reason"] == "API key missing"


def test_tier_gated_403_warns_with_single_component_token(monkeypatch, tmp_path):
    cmc = _load_module()
    _patch_output_paths(monkeypatch, cmc, tmp_path)
    monkeypatch.setattr(cmc, "_load_api_key", lambda: "dummy")

    def fake_fetch(endpoint, api_key, params=None):
        if endpoint == cmc.ENDPOINT_NARRATIVES:
            return {"data": [{"id": 1}]}, None
        if endpoint == cmc.ENDPOINT_MACRO:
            return None, "HTTP 403"
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    monkeypatch.setattr(cmc, "_fetch_api_with_retry", fake_fetch)

    assert cmc.main() == 0

    coverage = json.loads((tmp_path / "cmc_market_intel_coverage.json").read_text())
    assert coverage["status"] == "WARN"
    assert coverage["reason"] == "tier_gated:macro_events"


def test_tier_gated_403_warns_with_sorted_component_token(monkeypatch, tmp_path):
    cmc = _load_module()
    _patch_output_paths(monkeypatch, cmc, tmp_path)
    monkeypatch.setattr(cmc, "_load_api_key", lambda: "dummy")
    monkeypatch.setattr(cmc, "_fetch_api_with_retry", lambda endpoint, api_key, params=None: (None, "HTTP 403"))

    assert cmc.main() == 0

    coverage = json.loads((tmp_path / "cmc_market_intel_coverage.json").read_text())
    assert coverage["status"] == "WARN"
    assert coverage["reason"] == "tier_gated:macro_events,narratives"
