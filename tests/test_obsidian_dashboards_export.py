from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import obsidian_dashboards_export as exporter  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_export_dashboards_writes_expected_pages(tmp_path: Path) -> None:
    state_dir = tmp_path / "data" / "state"
    _write_json(
        state_dir / "system_health_latest.json",
        {
            "generated_utc": "2026-03-05T00:00:00Z",
            "ssot_status": "WARN",
            "components": {
                "freshness": {"status": "OK", "top_reason": "fresh"},
                "coverage": {"status": "WARN", "top_reason": "blocked pair"},
            },
        },
    )
    _write_json(
        state_dir / "freshness_table.json",
        {
            "generated_utc": "2026-03-05T00:00:00Z",
            "ts_utc": "2026-03-05T00:00:00Z",
            "default_profile": "default",
            "rows": [
                {"symbol": "BTCUSDT", "tf": "1m", "profile": "default", "status": "OK", "lag_sec": 12},
                {"symbol": "ETHUSDT", "tf": "1m", "profile": "default", "status": "WARN", "lag_sec": 90},
            ],
        },
    )
    _write_json(
        state_dir / "coverage_matrix_latest.json",
        {
            "ts_utc": "2026-03-05T00:00:00Z",
            "totals": {"done": 8, "inProgress": 1, "blocked": 2, "needs_rebase": 1},
            "rows": [
                {"symbol": "BTCUSDT", "status": "DONE"},
                {"symbol": "ETHUSDT", "status": "BLOCKED"},
            ],
        },
    )
    _write_json(
        state_dir / "brake_health_latest.json",
        {
            "ts_utc": "2026-03-05T00:00:00Z",
            "status": "WARN",
            "overall_fail": False,
            "results": [
                {"name": "position_guard", "status": "OK", "reason": "safe"},
                {"name": "latency_guard", "status": "WARN", "reason": "lag high"},
            ],
        },
    )
    _write_json(
        state_dir / "regime_monitor_latest.json",
        {
            "ts_utc": "2026-03-05T00:00:00Z",
            "overall": "RISK_OFF",
            "reason": ["volatility high"],
            "threshold_metric": "vol",
            "threshold_value": 0.8,
            "threshold_observed_value": 1.1,
            "suggestion": "reduce exposure",
        },
    )
    _write_json(
        state_dir / "data_catalog_latest.json",
        {
            "ts_utc": "2026-03-05T00:00:00Z",
            "datasets": [{"name": "btc_1m"}, {"name": "eth_1m"}],
        },
    )

    result = exporter.export_dashboards(
        repo_root=tmp_path,
        generated_utc="2026-03-05T01:02:03Z",
    )

    output_dir = tmp_path / "_local" / "obsidian_vault" / "HONGSTR" / "Dashboards"
    assert output_dir.exists()
    assert set(result["files_written"]) == {
        "10-HealthPack.md",
        "20-Freshness.md",
        "30-Coverage.md",
        "40-Brakes.md",
        "50-Regime.md",
    }

    health_text = (output_dir / "10-HealthPack.md").read_text(encoding="utf-8")
    assert "# 10-HealthPack" in health_text
    assert "generated_utc: `2026-03-05T01:02:03Z`" in health_text
    assert "`data/state/system_health_latest.json`" in health_text
    assert "| component | status | detail |" in health_text

    fresh_text = (output_dir / "20-Freshness.md").read_text(encoding="utf-8")
    assert "# 20-Freshness" in fresh_text
    assert "`data/state/freshness_table.json`" in fresh_text
    assert "| symbol_or_dataset | tf | profile | status | lag_sec |" in fresh_text

    coverage_text = (output_dir / "30-Coverage.md").read_text(encoding="utf-8")
    assert "# 30-Coverage" in coverage_text
    assert "| metric | value |" in coverage_text

    brakes_text = (output_dir / "40-Brakes.md").read_text(encoding="utf-8")
    assert "# 40-Brakes" in brakes_text
    assert "| check | status | detail |" in brakes_text

    regime_text = (output_dir / "50-Regime.md").read_text(encoding="utf-8")
    assert "# 50-Regime" in regime_text
    assert "| field | value |" in regime_text


def test_exporter_main_non_blocking_with_missing_sources(tmp_path: Path) -> None:
    script = SCRIPTS_DIR / "obsidian_dashboards_export.py"
    env = os.environ.copy()
    env["HONGSTR_REPO_ROOT"] = str(tmp_path)
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0
    assert "WARN obsidian_dashboards_export: source_missing" in completed.stderr
