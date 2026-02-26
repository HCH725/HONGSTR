import importlib.util
import json
from pathlib import Path


REPO = Path("/Users/hong/Projects/HONGSTR")
SCRIPT = REPO / "scripts/state_snapshots.py"
CASE_FIXTURE = REPO / "tests/fixtures/freshness_profiles/cases.json"


def _load_state_snapshots_module():
    spec = importlib.util.spec_from_file_location("state_snapshots_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_profile_thresholds_shape():
    mod = _load_state_snapshots_module()
    thresholds = mod.FRESHNESS_THRESHOLDS

    assert set(thresholds.keys()) == {"realtime", "backtest"}
    for profile in ("realtime", "backtest"):
        assert set(thresholds[profile].keys()) == {"ok_h", "warn_h", "fail_h"}


def test_profile_split_for_backtest_vs_realtime_20h():
    mod = _load_state_snapshots_module()
    cases = json.loads(CASE_FIXTURE.read_text(encoding="utf-8"))

    for case in cases:
        profile = mod._freshness_profile_from_source(case["source"], tags=[])
        status, _ = mod._evaluate_freshness_status(case["age_h"], profile, None)
        assert profile == case["expected_profile"], case["name"]
        assert status == case["expected_status"], case["name"]


def test_missing_source_keeps_fail():
    mod = _load_state_snapshots_module()
    status, reason = mod._evaluate_freshness_status(None, "realtime", "missing_source")
    assert status == "FAIL"
    assert reason == "missing_source"
