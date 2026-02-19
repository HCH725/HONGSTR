import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path to import generate_gate
sys.path.append(str(Path(__file__).parent.parent))

from scripts.generate_gate_artifact import generate_gate


@pytest.fixture
def mock_artifacts(tmp_path):
    run_dir = tmp_path / "mock_run"
    run_dir.mkdir()

    # Fake config
    config = {
        "min_trades_per_day": 1.0, # 1 trade per day
        "min_trades_portfolio_min": 10,
        "min_trades_per_symbol_min": 5,
        "per_symbol_trade_check": "WARN",
        "exposure_check": "WARN",
        "max_exposure": 0.5,
        "thresholds": {"SHORT": {"ANY": {"min_sharpe": 0.0, "max_mdd": -1.0}}}
    }

    # Fake Summary (10 days)
    summary = {
        "start_ts": "2024-01-01T00:00:00Z",
        "end_ts": "2024-01-10T00:00:00Z", # 10 days inclusive? (10-01).days = 9. +1 = 10.
        "trades_count": 20, # > 10 required
        "exposure_time": 0.2,
        "per_symbol": {
            "BTCUSDT": {"trades_count": 15},
            "ETHUSDT": {"trades_count": 5}
        }
    }

    # Fake Regime Report
    regime = {
        "buckets": {
            "BULL": {"sharpe": 1.0, "max_drawdown": -0.1, "trades_count": 10},
            "BEAR": {"sharpe": 0.5, "max_drawdown": -0.05, "trades_count": 10},
            "NEUTRAL": {}
        }
    }

    return run_dir, config, summary, regime

def test_adaptive_pass(mock_artifacts):
    run_dir, config, summary, regime = mock_artifacts

    with patch("scripts.generate_gate_artifact.load_json") as mock_load:
        with patch("scripts.generate_gate_artifact.save_json_atomic") as mock_save:
            # Mock returns: regime, summary, config
            mock_load.side_effect = [regime, summary, config]

            generate_gate(run_dir, "SHORT", ["BTCUSDT", "ETHUSDT"], "4h")

            # Verify Pass
            args, _ = mock_save.call_args
            gate_data = args[1]
            assert gate_data["results"]["overall"]["pass"] is True
            assert gate_data["inputs"]["required_trades"] == 10 # 10 days * 1.0
            assert gate_data["inputs"]["window_days"] == 10

def test_adaptive_fail_portfolio(mock_artifacts):
    run_dir, config, summary, regime = mock_artifacts
    summary["trades_count"] = 5 # Below required 10

    with patch("scripts.generate_gate_artifact.load_json") as mock_load:
        with patch("scripts.generate_gate_artifact.save_json_atomic") as mock_save:
            mock_load.side_effect = [regime, summary, config]

            generate_gate(run_dir, "SHORT", ["BTCUSDT", "ETHUSDT"], "4h")

            args, _ = mock_save.call_args
            gate_data = args[1]
            assert gate_data["results"]["overall"]["pass"] is False
            assert "Portfolio Trades 5 < Required 10" in gate_data["results"]["overall"]["reasons"][0]

def test_per_symbol_warn(mock_artifacts):
    run_dir, config, summary, regime = mock_artifacts
    summary["per_symbol"]["ETHUSDT"]["trades_count"] = 2 # Below 5

    with patch("scripts.generate_gate_artifact.load_json") as mock_load:
        with patch("scripts.generate_gate_artifact.save_json_atomic") as mock_save:
            mock_load.side_effect = [regime, summary, config]

            generate_gate(run_dir, "SHORT", ["BTCUSDT", "ETHUSDT"], "4h")

            args, _ = mock_save.call_args
            gate_data = args[1]
            assert gate_data["results"]["overall"]["pass"] is True # Should pass with WARN
            reasons = gate_data["results"]["overall"]["reasons"]
            assert any("[WARN] Symbol ETHUSDT Trades 2 < 5" in r for r in reasons)

def test_per_symbol_fail(mock_artifacts):
    run_dir, config, summary, regime = mock_artifacts
    config["per_symbol_trade_check"] = "FAIL"
    summary["per_symbol"]["ETHUSDT"]["trades_count"] = 2

    with patch("scripts.generate_gate_artifact.load_json") as mock_load:
        with patch("scripts.generate_gate_artifact.save_json_atomic") as mock_save:
            mock_load.side_effect = [regime, summary, config]

            generate_gate(run_dir, "SHORT", ["BTCUSDT", "ETHUSDT"], "4h")

            args, _ = mock_save.call_args
            gate_data = args[1]
            assert gate_data["results"]["overall"]["pass"] is False
            reasons = gate_data["results"]["overall"]["reasons"]
            assert any("Symbol ETHUSDT Trades 2 < 5" in r for r in reasons)

def test_exposure_warn(mock_artifacts):
    run_dir, config, summary, regime = mock_artifacts
    summary["exposure_time"] = 0.8 # > 0.5 max

    with patch("scripts.generate_gate_artifact.load_json") as mock_load:
        with patch("scripts.generate_gate_artifact.save_json_atomic") as mock_save:
            mock_load.side_effect = [regime, summary, config]

            generate_gate(run_dir, "SHORT", ["BTCUSDT", "ETHUSDT"], "4h")

            args, _ = mock_save.call_args
            gate_data = args[1]
            assert gate_data["results"]["overall"]["pass"] is True
            reasons = gate_data["results"]["overall"]["reasons"]
            assert any("[WARN] Exposure 0.80 > 0.5" in r for r in reasons)

def test_exposure_fail(mock_artifacts):
    run_dir, config, summary, regime = mock_artifacts
    summary["exposure_time"] = 0.8
    config["exposure_check"] = "FAIL"

    with patch("scripts.generate_gate_artifact.load_json") as mock_load:
        with patch("scripts.generate_gate_artifact.save_json_atomic") as mock_save:
            mock_load.side_effect = [regime, summary, config]

            generate_gate(run_dir, "SHORT", ["BTCUSDT", "ETHUSDT"], "4h")

            args, _ = mock_save.call_args
            gate_data = args[1]
            assert gate_data["results"]["overall"]["pass"] is False
            reasons = gate_data["results"]["overall"]["reasons"]
            assert any("Exposure 0.80 > 0.5" in r for r in reasons)
