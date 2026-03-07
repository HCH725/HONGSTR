import importlib.util
import json
import subprocess
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "cmc_market_intel_fetch.py"


def _load_cmc_module():
    module_name = f"cmc_market_intel_fetch_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _patch_output_paths(module, tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DERIVED_ROOT_NARRATIVES", tmp_path / "derived" / "narratives")
    monkeypatch.setattr(module, "DERIVED_ROOT_MACRO", tmp_path / "derived" / "macro_events")
    monkeypatch.setattr(module, "ATOMIC_COVERAGE_PATH", tmp_path / "reports" / "cmc_market_intel_coverage.json")
    monkeypatch.setattr(module, "MANIFEST_PATH", tmp_path / "reports" / "manifests" / "cmc_market_intel_v1.json")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_missing_key_marks_fail_and_keeps_reason_deterministic(tmp_path, monkeypatch):
    module = _load_cmc_module()
    _patch_output_paths(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module, "_load_api_key", lambda: None)

    rc = module.main()

    coverage = _read_json(module.ATOMIC_COVERAGE_PATH)
    assert rc == 0
    assert coverage["status"] == "FAIL"
    assert coverage["reason"] == "API key missing"


def test_http_403_tier_gated_marks_warn_and_skips_component(tmp_path, monkeypatch):
    module = _load_cmc_module()
    _patch_output_paths(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module, "_load_api_key", lambda: "dummy")

    def fake_fetch(endpoint, api_key, params=None):
        if endpoint == module.ENDPOINT_NARRATIVES:
            return {"data": [{"id": 1}]}, None
        if endpoint == module.ENDPOINT_MACRO:
            return None, module.HTTP_403_TIER_GATED
        raise AssertionError(f"Unexpected endpoint {endpoint}")

    monkeypatch.setattr(module, "_fetch_api_with_retry", fake_fetch)

    rc = module.main()

    coverage = _read_json(module.ATOMIC_COVERAGE_PATH)
    assert rc == 0
    assert coverage["status"] == "WARN"
    assert coverage["reason"] == "tier_gated:macro_events"
    assert coverage["items"]["narratives_count"] == 1
    assert coverage["items"]["macro_events_count"] == 0


def test_http_403_tier_gated_multiple_components_collapses_reason(tmp_path, monkeypatch):
    module = _load_cmc_module()
    _patch_output_paths(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module, "_load_api_key", lambda: "dummy")
    monkeypatch.setattr(
        module,
        "_fetch_api_with_retry",
        lambda endpoint, api_key, params=None: (None, module.HTTP_403_TIER_GATED),
    )

    rc = module.main()

    coverage = _read_json(module.ATOMIC_COVERAGE_PATH)
    assert rc == 0
    assert coverage["status"] == "WARN"
    assert coverage["reason"] == "tier_gated:macro_events,narratives"


def test_non_403_http_error_marks_fail_with_deterministic_reason(tmp_path, monkeypatch):
    module = _load_cmc_module()
    _patch_output_paths(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module, "_load_api_key", lambda: "dummy")

    def fake_fetch(endpoint, api_key, params=None):
        if endpoint == module.ENDPOINT_NARRATIVES:
            return {"data": [{"id": 1}]}, None
        if endpoint == module.ENDPOINT_MACRO:
            return None, "http_500"
        raise AssertionError(f"Unexpected endpoint {endpoint}")

    monkeypatch.setattr(module, "_fetch_api_with_retry", fake_fetch)

    rc = module.main()

    coverage = _read_json(module.ATOMIC_COVERAGE_PATH)
    assert rc == 0
    assert coverage["status"] == "FAIL"
    assert coverage["reason"] == "http_500:macro_events"


def test_refresh_state_keeps_running_with_tier_gated_warn(monkeypatch):
    module = _load_cmc_module()
    atomic_path = REPO_ROOT / "reports" / "state_atomic" / "cmc_market_intel_coverage.json"
    state_path = REPO_ROOT / "data" / "state" / "cmc_market_intel_coverage_latest.json"

    monkeypatch.setattr(module, "_load_api_key", lambda: "dummy")
    monkeypatch.setattr(
        module,
        "_fetch_api_with_retry",
        lambda endpoint, api_key, params=None: (None, module.HTTP_403_TIER_GATED),
    )

    rc = module.main()
    refresh = subprocess.run(
        ["bash", "scripts/refresh_state.sh"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert rc == 0
    assert refresh.returncode == 0, refresh.stderr
    assert atomic_path.exists()
    assert state_path.exists()

    atomic_payload = _read_json(atomic_path)
    state_payload = _read_json(state_path)
    assert atomic_payload["status"] == "WARN"
    assert atomic_payload["reason"] == "tier_gated:macro_events,narratives"
    assert state_payload["status"] == "WARN"
    assert state_payload["reason"] == "tier_gated:macro_events,narratives"
