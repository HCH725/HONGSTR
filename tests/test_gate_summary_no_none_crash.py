import json
import runpy

import pytest


def test_gate_summary_does_not_crash_on_none_metrics(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    summary = run_dir / "summary.json"
    gate = run_dir / "gate.json"

    summary.write_text(
        json.dumps(
            {
                "trades_count": 0,
                "sharpe": None,
                "total_return": None,
                "per_symbol": {
                    "BTCUSDT_1h": {
                        "trades_count": 0,
                        "total_return": None,
                        "max_drawdown": None,
                        "sharpe": None,
                        "exposure_time": None,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    gate.write_text(
        json.dumps({"results": {"overall": {"pass": True, "reasons": []}}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        ["gate_summary.py", "--summary", str(summary), "--symbols", "BTCUSDT", "--timeframes", "1h"],
    )

    with pytest.raises(SystemExit) as exc:
        runpy.run_path("scripts/gate_summary.py", run_name="__main__")

    assert exc.value.code == 0
