import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/state_snapshots.py"
CASE_FIXTURE = REPO / "tests/fixtures/freshness_profiles/cases.json"
CANONICAL_FIXTURE = REPO / "tests/fixtures/freshness_profiles/canonicalize_cases.json"


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
    assert thresholds["realtime"] == {"ok_h": 0.1, "warn_h": 0.25, "fail_h": 1.0}
    assert thresholds["backtest"] == {"ok_h": 26.0, "warn_h": 50.0, "fail_h": 72.0}
    assert mod.DEFAULT_FRESHNESS_PROFILE == "realtime"


def test_profile_split_for_backtest_vs_realtime_20h():
    mod = _load_state_snapshots_module()
    cases = json.loads(CASE_FIXTURE.read_text(encoding="utf-8"))

    for case in cases:
        profile = mod._freshness_profile_from_source(case["source"], mod.DEFAULT_FRESHNESS_PROFILE)
        status, _ = mod._evaluate_freshness_status(case["age_h"], profile, None)
        assert profile == case["expected_profile"], case["name"]
        assert status == case["expected_status"], case["name"]


def test_profile_default_is_explicit():
    mod = _load_state_snapshots_module()
    assert mod._freshness_profile_from_source("logs/etl.log", mod.DEFAULT_FRESHNESS_PROFILE) == "realtime"


def test_canonicalize_row_enforces_deterministic_schema_and_defaults():
    mod = _load_state_snapshots_module()
    cases = json.loads(CANONICAL_FIXTURE.read_text(encoding="utf-8"))
    expected_keys = ["symbol", "tf", "profile", "age_h", "status", "source", "reason"]

    for case in cases:
        row = mod._canonicalize_freshness_row(
            symbol=case.get("symbol"),
            tf=case.get("tf"),
            profile=case.get("profile"),
            age_h=case.get("age_h"),
            status=case.get("status"),
            source=case.get("source"),
            reason=case.get("reason"),
        )
        assert list(row.keys()) == expected_keys, case["name"]

        expected = case["expected"]
        for key in expected_keys:
            assert row[key] == expected[key], f"{case['name']}::{key}"


def test_build_freshness_table_includes_required_top_level_keys():
    mod = _load_state_snapshots_module()
    row = mod._canonicalize_freshness_row(
        symbol="BTCUSDT",
        tf="1m",
        profile=None,
        age_h=20.0,
        status="WARN",
        source="",
        reason=None,
    )

    table = mod._build_freshness_table("2026-02-26T00:00:00Z", [row])

    assert "generated_utc" in table
    assert "ts_utc" in table
    assert "thresholds" in table
    assert "rows" in table
    assert table["generated_utc"] == "2026-02-26T00:00:00Z"
    assert table["ts_utc"] == "2026-02-26T00:00:00Z"
    assert isinstance(table["thresholds"], dict)
    assert isinstance(table["rows"], list)
