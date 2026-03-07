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
    spec = importlib.util.spec_from_file_location("state_snapshots_dq_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_freshness_gate_marks_warn_and_fail_rows_unusable():
    mod = _load_state_snapshots_module()

    ok_row = mod._canonicalize_freshness_row(
        symbol="BTCUSDT",
        tf="1m",
        profile="realtime",
        age_h=0.0,
        status="OK",
        source="data/derived/BTCUSDT/1m/klines.jsonl",
        reason="",
    )
    stale_row = mod._canonicalize_freshness_row(
        symbol="ETHUSDT",
        tf="1h",
        profile="backtest",
        age_h=29.0,
        status="WARN",
        source="data/derived/ETHUSDT/1h/klines.jsonl",
        reason="stale",
    )
    missing_row = mod._canonicalize_freshness_row(
        symbol="BNBUSDT",
        tf="4h",
        profile="backtest",
        age_h=None,
        status="FAIL",
        source="data/derived/BNBUSDT/4h/klines.jsonl",
        reason="missing_source",
    )

    assert ok_row["is_usable"] is True
    assert ok_row["unusable_reason"] == ""
    assert stale_row["is_usable"] is False
    assert stale_row["unusable_reason"] == "stale"
    assert missing_row["is_usable"] is False
    assert missing_row["unusable_reason"] == "missing_source"


def test_coverage_gate_marks_non_pass_rows_unusable():
    mod = _load_state_snapshots_module()

    assert mod._coverage_gate_fields("DONE") == ("PASS", True, "")
    assert mod._coverage_gate_fields("IN_PROGRESS") == ("WARN", False, "coverage_in_progress")
    assert mod._coverage_gate_fields("BLOCKED_DATA_QUALITY") == ("FAIL", False, "blocked_data_quality")
    assert mod._coverage_gate_fields("NEEDS_REBASE") == ("NEEDS_REBASE", False, "needs_rebase")


def test_data_quality_gate_component_fails_when_any_row_unusable():
    mod = _load_state_snapshots_module()
    freshness_rows = [
        {"symbol": "BTCUSDT", "tf": "1m", "status": "OK", "is_usable": True, "unusable_reason": ""},
        {"symbol": "ETHUSDT", "tf": "1h", "status": "WARN", "is_usable": False, "unusable_reason": "stale"},
    ]
    coverage_rows = [
        {"symbol": "BTCUSDT", "tf": "1h", "status": "PASS", "is_usable": True, "unusable_reason": ""},
        {"symbol": "ETHUSDT", "tf": "4h", "status": "FAIL", "is_usable": False, "unusable_reason": "blocked_data_quality"},
    ]

    gate = mod._build_data_quality_gate_component(freshness_rows, coverage_rows)

    assert gate["status"] == "FAIL"
    assert gate["is_usable"] is False
    assert gate["freshness_rows_total"] == 2
    assert gate["coverage_rows_total"] == 2
    assert len(gate["blocking_rows"]) == 2
    assert {row["kind"] for row in gate["blocking_rows"]} == {"freshness", "coverage_matrix"}


def test_main_publishes_machine_checkable_data_quality_gate(tmp_path: Path, monkeypatch):
    mod = _load_state_snapshots_module()
    monkeypatch.chdir(tmp_path)

    derived = tmp_path / "data" / "derived"
    good_path = derived / "BTCUSDT" / "1m"
    good_path.mkdir(parents=True, exist_ok=True)
    (good_path / "klines.jsonl").write_text('{"ts": 1700000000000, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}\n', encoding="utf-8")

    coverage_atomic = tmp_path / "reports" / "state_atomic" / "coverage_table.jsonl"
    coverage_atomic.parent.mkdir(parents=True, exist_ok=True)
    coverage_atomic.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "coverage_key": {"symbol": "BTCUSDT", "timeframe": "1m", "regime": "ALL"},
                        "status": "DONE",
                        "created_utc": "2026-03-08T00:00:00Z",
                        "updated_utc": "2026-03-08T00:00:00Z",
                        "results": {"is": {"start": "2020-01-01", "end": "2025-12-31"}, "oos": {"end": "now"}},
                    }
                ),
                json.dumps(
                    {
                        "coverage_key": {"symbol": "ETHUSDT", "timeframe": "1h", "regime": "ALL"},
                        "status": "BLOCKED_DATA_QUALITY",
                        "created_utc": "2026-03-08T00:00:00Z",
                        "updated_utc": "2026-03-08T00:00:00Z",
                        "results": {"is": {"start": "2020-01-01", "end": "2025-12-31"}, "oos": {"end": "2026-03-07"}},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    mod.main()

    freshness = json.loads((tmp_path / "data" / "state" / "freshness_table.json").read_text(encoding="utf-8"))
    coverage = json.loads((tmp_path / "data" / "state" / "coverage_matrix_latest.json").read_text(encoding="utf-8"))
    system_health = json.loads((tmp_path / "data" / "state" / "system_health_latest.json").read_text(encoding="utf-8"))
    daily_report = json.loads((tmp_path / "data" / "state" / "daily_report_latest.json").read_text(encoding="utf-8"))

    assert freshness["quality_gate"]["is_usable"] is False
    assert any(row["is_usable"] is False for row in freshness["rows"])
    assert any(row["unusable_reason"] == "missing_source" for row in freshness["rows"])

    eth_cov = next(row for row in coverage["rows"] if row["symbol"] == "ETHUSDT" and row["tf"] == "1h")
    assert eth_cov["is_usable"] is False
    assert eth_cov["unusable_reason"] == "blocked_data_quality"

    dq_gate = system_health["components"]["data_quality_gate"]
    assert dq_gate["status"] == "FAIL"
    assert dq_gate["is_usable"] is False
    assert len(dq_gate["blocking_rows"]) >= 1

    assert daily_report["ssot_components"]["data_quality_gate"]["status"] == "FAIL"
    assert daily_report["ssot_components"]["data_quality_gate"]["is_usable"] is False
