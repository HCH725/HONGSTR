import pytest
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts to path
sys.path.append(str(Path(__file__).parent.parent))
from scripts.generate_action_items import generate_action_items

@pytest.fixture
def mock_reports_dir(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    
    # Mock walkforward_latest.json
    wf_data = {
        "generated_at": "2024-01-01T00:00:00Z",
        "windows": []
    }
    with open(d / "walkforward_latest.json", "w") as f:
        json.dump(wf_data, f)
        
    return d

@pytest.fixture
def mock_data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "backtests").mkdir()
    return d

def run_gen(reports, data):
    generate_action_items(reports, data)
    out_json = reports / "action_items_latest.json"
    assert out_json.exists()
    with open(out_json) as f:
        return json.load(f)

def test_heuristic_low_trades(mock_reports_dir, mock_data_dir):
    # Setup WF data with Low Trades failure
    wf = json.load(open(mock_reports_dir / "walkforward_latest.json"))
    wf["windows"] = [{
        "name": "TEST_WIN",
        "gate_overall": "FAIL",
        "trades": 5, # Low
        "sharpe": 1.0,
        "notes": "Decision: HOLD"
    }]
    with open(mock_reports_dir / "walkforward_latest.json", "w") as f:
        json.dump(wf, f)
        
    res = run_gen(mock_reports_dir, mock_data_dir)
    assert res["overall_gate"] == "FAIL"
    top = res["top_actions"][0]
    assert "Increase Signal Frequency" in top["title"]
    assert "Low Trades" in top["title"]

def test_heuristic_low_sharpe(mock_reports_dir, mock_data_dir):
    wf = json.load(open(mock_reports_dir / "walkforward_latest.json"))
    wf["windows"] = [{
        "name": "TEST_WIN",
        "gate_overall": "FAIL",
        "trades": 100,
        "sharpe": -0.5, # Low
        "notes": "Decision: HOLD"
    }]
    with open(mock_reports_dir / "walkforward_latest.json", "w") as f:
        json.dump(wf, f)
        
    res = run_gen(mock_reports_dir, mock_data_dir)
    top = res["top_actions"][0]
    assert "Improve Signal Quality" in top["title"]

def test_heuristic_high_mdd(mock_reports_dir, mock_data_dir):
    wf = json.load(open(mock_reports_dir / "walkforward_latest.json"))
    wf["windows"] = [{
        "name": "TEST_WIN",
        "gate_overall": "FAIL",
        "trades": 50,
        "sharpe": 0.5,
        "mdd": -0.4, # Deep
        "notes": "Decision: HOLD"
    }]
    with open(mock_reports_dir / "walkforward_latest.json", "w") as f:
        json.dump(wf, f)
        
    res = run_gen(mock_reports_dir, mock_data_dir)
    # Could be diverse ranking, check if present
    titles = [a["title"] for a in res["top_actions"]]
    assert any("Tighten Risk Controls" in t for t in titles)

def test_heuristic_exposure(mock_reports_dir, mock_data_dir):
    wf = json.load(open(mock_reports_dir / "walkforward_latest.json"))
    wf["windows"] = [{
        "name": "TEST_WIN",
        "gate_overall": "FAIL",
        # Script does: notes = w.get("notes", "").lower() 
        # So "Exposure" becomes "exposure".
        # But let's be explicit in mock to be sure.
        "notes": "gate: fail; exposure > 0.99"
    }]
    with open(mock_reports_dir / "walkforward_latest.json", "w") as f:
        json.dump(wf, f)
        
    res = run_gen(mock_reports_dir, mock_data_dir)
    titles = [a["title"] for a in res["top_actions"]]
    assert any("Reduce Market Exposure" in t for t in titles)

def test_pass_state(mock_reports_dir, mock_data_dir):
    wf = json.load(open(mock_reports_dir / "walkforward_latest.json"))
    wf["windows"] = [{
        "name": "TEST_WIN",
        "gate_overall": "PASS",
        "trades": 50,
        "sharpe": 2.0
    }]
    with open(mock_reports_dir / "walkforward_latest.json", "w") as f:
        json.dump(wf, f)
        
    res = run_gen(mock_reports_dir, mock_data_dir)
    assert res["overall_gate"] == "PASS"
    assert len(res["top_actions"]) == 0
