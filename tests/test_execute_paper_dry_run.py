import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.append(str(Path(__file__).parent.parent))
from scripts.execute_paper import main as execute_main

def test_execute_dry_run_no_network(tmp_path):
    """Verify that DRY-RUN mode doesn't hit the network or broker."""
    # Mock selection.json
    d = tmp_path / "backtests" / "2024-01-01" / "test_run"
    d.mkdir(parents=True)
    sel_path = d / "selection.json"
    import json
    with open(sel_path, "w") as f:
        json.dump({"decision": "TRADE", "regime": "BULL", "selected_symbol": "BTCUSDT"}, f)
    
    with patch("scripts.execute_paper.BinanceFuturesTestnetBroker") as mock_broker:
        with patch("requests.get") as mock_get:
            with patch("sys.argv", ["execute_paper.py", "--run_dir", str(d), "--data_dir", str(tmp_path)]):
                # Ensure no --send flag
                execute_main()
                
                # Verify no broker instance was created
                assert mock_broker.call_count == 0
                # Verify no network calls via requests
                assert mock_get.call_count == 0
                
def test_execute_send_hits_network(tmp_path):
    """Verify that --send mode DOES hit the network."""
    d = tmp_path / "backtests" / "2024-01-01" / "test_run"
    d.mkdir(parents=True)
    sel_path = d / "selection.json"
    import json
    with open(sel_path, "w") as f:
        json.dump({"decision": "TRADE", "regime": "BULL", "selected_symbol": "BTCUSDT"}, f)
        
    with patch("scripts.execute_paper.BinanceFuturesTestnetBroker") as mock_broker:
        mock_instance = mock_broker.return_value
        mock_instance.base_url = "http://mock"
        mock_instance.place_order.return_value = MagicMock(exchange_order_id="123")
        # Return a dict instead of MagicMock to allow JSON serialization
        mock_instance.get_order.return_value = {
            "orderId": "123",
            "clientOrderId": "abc",
            "status": "NEW",
            "avgPrice": "0",
            "executedQty": "0"
        }
        
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {"price": "50000.0"})
            
            with patch("sys.argv", ["execute_paper.py", "--run_dir", str(d), "--data_dir", str(tmp_path), "--send"]):
                execute_main()
                
                # Verify broker and network were hit
                assert mock_broker.call_count == 1
                assert mock_get.call_count == 1
