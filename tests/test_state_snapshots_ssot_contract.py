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
    spec = importlib.util.spec_from_file_location("state_snapshots_ssot_contract_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_main_publishes_consistent_ssot_contract_for_readiness_freshness_and_coverage(tmp_path: Path, monkeypatch):
    mod = _load_state_snapshots_module()
    monkeypatch.chdir(tmp_path)

    derived = tmp_path / "data" / "derived"
    good_path = derived / "BTCUSDT" / "1m"
    good_path.mkdir(parents=True, exist_ok=True)
    (good_path / "klines.jsonl").write_text(
        '{"ts": 1700000000000, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}\n',
        encoding="utf-8",
    )

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
                        "coverage_key": {"symbol": "ETHUSDT", "timeframe": "4h", "regime": "ALL"},
                        "status": "IN_PROGRESS",
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

    assert freshness["contract"]["version"] == mod.DATA_PLANE_SSOT_CONTRACT_VERSION
    assert freshness["contract"]["canonical_path"] == "data/state/freshness_table.json"
    assert freshness["contract"]["reason_field"] == "rows[].reason"
    assert freshness["contract"]["source_field"] == "rows[].source"
    assert freshness["contract"]["evidence_field"] == "rows[].evidence"
    assert freshness["contract"]["consumer_mode"] == "read_only"

    fresh_row = next(row for row in freshness["rows"] if row["symbol"] == "BTCUSDT" and row["tf"] == "1m")
    assert fresh_row["source"] == "data/derived/BTCUSDT/1m/klines.jsonl"
    assert fresh_row["evidence"]["type"] == "path_mtime"
    assert fresh_row["evidence"]["ref"] == "data/derived/BTCUSDT/1m/klines.jsonl"

    assert coverage["contract"]["version"] == mod.DATA_PLANE_SSOT_CONTRACT_VERSION
    assert coverage["contract"]["canonical_path"] == "data/state/coverage_matrix_latest.json"
    assert coverage["contract"]["reason_field"] == "rows[].reason"
    assert coverage["contract"]["source_field"] == "rows[].source"
    assert coverage["contract"]["evidence_field"] == "rows[].evidence"
    assert coverage["contract"]["consumer_mode"] == "read_only"

    eth_cov = next(row for row in coverage["rows"] if row["symbol"] == "ETHUSDT" and row["tf"] == "4h")
    assert eth_cov["reason"] == "coverage_in_progress"
    assert eth_cov["source"] == "data/state/coverage_table.jsonl"
    assert eth_cov["evidence"]["type"] == "coverage_table_row"
    assert eth_cov["evidence"]["ref"] == "data/state/coverage_table.jsonl#ETHUSDT:4h:ALL"

    assert system_health["contract"] == mod._system_health_contract()
    assert system_health["ssot_source"] == "data/state/system_health_latest.json"
    assert system_health["ssot_evidence"]["type"] == "state_snapshot"
    assert system_health["ssot_evidence"]["ref"] == "data/state/system_health_latest.json#components"
    assert system_health["components"]["freshness"]["source"] == "data/state/freshness_table.json"
    assert system_health["components"]["freshness"]["evidence"]["ref"] == "data/state/freshness_table.json#quality_gate"
    assert system_health["components"]["coverage_matrix"]["source"] == "data/state/coverage_matrix_latest.json"
    assert system_health["components"]["coverage_matrix"]["evidence"]["ref"] == "data/state/coverage_matrix_latest.json#quality_gate"

    assert daily_report["sources"]["system_health_latest"]["path"] == "data/state/system_health_latest.json"
    assert daily_report["sources"]["freshness_table"]["path"] == "data/state/freshness_table.json"
    assert daily_report["sources"]["coverage_matrix_latest"]["path"] == "data/state/coverage_matrix_latest.json"
