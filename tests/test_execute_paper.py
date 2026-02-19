import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path
sys.path.append(str(Path(__file__).parent.parent))
from scripts.execute_paper import main as execute_main


@pytest.fixture
def mock_selection_file(tmp_path):
    d = tmp_path / "backtests" / "2024-01-01" / "test_run"
    d.mkdir(parents=True)
    sel_path = d / "selection.json"
    return sel_path

def test_execute_hold(mock_selection_file, tmp_path):
    """Test that HOLD decision generates no orders."""
    sel_data = {
        "decision": "HOLD",
        "regime": "BEAR",
        "selected_symbol": "BTCUSDT"
    }
    with open(mock_selection_file, "w") as f:
        json.dump(sel_data, f)

    # Run main with specified run_dir
    run_dir = str(mock_selection_file.parent)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    with patch("scripts.execute_paper.get_latest_selection", return_value=mock_selection_file):
        with patch("pathlib.Path.mkdir"): # Safety
             with patch("scripts.execute_paper.save_report") as mock_save:
                 with patch("scripts.execute_paper.generate_markdown_report"):
                    # We need to monkeypatch the reports directory in the script
                    # or just let it write to a temp reports folder.
                    # Let's mock the report savers to verify output data.

                    with patch("sys.argv", ["execute_paper.py", "--run_dir", run_dir]):
                        # We need to handle the 'reports' folder creation in the script
                        # For testing, let's just assert the data passed to save_report
                        execute_main()

                        args, _ = mock_save.call_args
                        # args[0] is path, args[1] is data
                        data = args[1]
                        assert data["decision"] == "HOLD"
                        assert len(data["orders"]) == 0

def test_execute_trade_dry_run(mock_selection_file, tmp_path):
    """Test that TRADE decision generates a DRY_RUN order."""
    sel_data = {
        "decision": "TRADE",
        "regime": "BULL",
        "selected_symbol": "ETHUSDT"
    }
    with open(mock_selection_file, "w") as f:
        json.dump(sel_data, f)

    run_dir = str(mock_selection_file.parent)

    with patch("scripts.execute_paper.save_report") as mock_save:
        with patch("scripts.execute_paper.generate_markdown_report"):
                with patch("sys.argv", ["execute_paper.py", "--run_dir", run_dir]):
                    execute_main()

                    args, kwargs = mock_save.call_args
                    data = args[1]
                    assert data["decision"] == "TRADE"
                    assert len(data["orders"]) == 1
                    assert data["orders"][0]["symbol"] == "ETHUSDT"
                    assert data["orders"][0]["status"] == "DRY_RUN"

def test_execute_notional_limit(mock_selection_file, tmp_path):
    """Test that orders exceeding max_notional_usd are rejected."""
    sel_data = {
        "decision": "TRADE",
        "regime": "BULL",
        "selected_symbol": "BTCUSDT"
    }
    with open(mock_selection_file, "w") as f:
        json.dump(sel_data, f)

    run_dir = str(mock_selection_file.parent)

    with patch("scripts.execute_paper.save_report") as mock_save:
        with patch("scripts.execute_paper.generate_markdown_report"):
            # Set a very low limit
            with patch("sys.argv", ["execute_paper.py", "--run_dir", run_dir, "--max_notional_usd", "5.0"]):
                execute_main()

                args, kwargs = mock_save.call_args
                data = args[1]
                assert len(data["orders"]) == 0
                assert "Rejected" in data["error"]
