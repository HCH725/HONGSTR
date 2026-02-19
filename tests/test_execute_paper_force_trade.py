import pytest
import os
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.append(str(Path(__file__).parent.parent))
from scripts.execute_paper import main as execute_main

def test_force_trade_rejected_on_production(tmp_path):
    """Verify that --force_trade is rejected if not in testnet mode."""
    # Ensure testnet env vars are NOT set
    with patch.dict(os.environ, {"BINANCE_FUTURES_TESTNET": "0", "BINANCE_TESTNET": "0"}, clear=False):
        with patch("sys.exit") as mock_exit:
            with patch("sys.argv", ["execute_paper.py", "--force_trade"]):
                execute_main()
                mock_exit.assert_called_with(1)

def test_force_trade_allowed_on_testnet_dry_run(tmp_path):
    """Verify that --force_trade is allowed on testnet and defaults to dry-run."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    
    # Mock search for selection.json to avoid failure
    with patch("scripts.execute_paper.get_latest_selection", return_value=None):
        with patch.dict(os.environ, {"BINANCE_FUTURES_TESTNET": "1"}):
            with patch("scripts.execute_paper.save_report") as mock_save:
                with patch("scripts.execute_paper.generate_markdown_report"):
                    with patch("sys.argv", ["execute_paper.py", "--force_trade", "--data_dir", str(tmp_path)]):
                        execute_main()
                        
                        args, _ = mock_save.call_args
                        data = args[1]
                        assert data["decision"] == "TRADE"
                        assert data["forced"] is True
                        assert data["dry_run"] is True
                        assert data["orders"][0]["forced"] is True
                        assert data["orders"][0]["status"] == "DRY_RUN"

def test_force_trade_respects_notional_limit(tmp_path):
    """Verify that forced trades still respect the max notional limit."""
    with patch.dict(os.environ, {"BINANCE_FUTURES_TESTNET": "1"}):
        with patch("scripts.execute_paper.save_report") as mock_save:
            with patch("scripts.execute_paper.generate_markdown_report"):
                # Force a trade with 100 USDT but max limit 50
                with patch("sys.argv", ["execute_paper.py", "--force_trade", "--force_notional_usd", "100.0", "--max_notional_usd", "50.0", "--data_dir", str(tmp_path)]):
                    execute_main()
                    
                    args, _ = mock_save.call_args
                    data = args[1]
                    assert len(data["orders"]) == 0
                    assert "Rejected" in data["error"]

def test_force_trade_with_send_hits_broker(tmp_path):
    """Verify --force_trade + --send executes mocked send path without real network."""
    with patch.dict(os.environ, {"BINANCE_FUTURES_TESTNET": "1"}):
        with patch("scripts.execute_paper.BinanceFuturesTestnetBroker") as mock_broker_cls:
            mock_instance = mock_broker_cls.return_value
            mock_instance.base_url = "http://mock"
            mock_instance.filters.round_qty.return_value = 0.001
            mock_instance.filters.get_filters.return_value = {"min_qty": 0.001}
            mock_instance.place_order.return_value = MagicMock(exchange_order_id="F123")
            mock_instance.get_order.return_value = {
                "orderId": "F123",
                "status": "FILLED",
                "avgPrice": "60000",
                "executedQty": "0.001",
                "clientOrderId": "abc123",
            }

            with patch("scripts.execute_paper.requests.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200, json=lambda: {"price": "60000.0"})

                with patch("scripts.execute_paper.save_report") as mock_save:
                    with patch("scripts.execute_paper.generate_markdown_report"):
                        with patch("sys.argv", ["execute_paper.py", "--force_trade", "--send", "--data_dir", str(tmp_path)]):
                            execute_main()

                            assert mock_instance.place_order.call_count == 1
                            assert mock_instance.get_order.call_count == 1
                            assert mock_get.call_count == 1
                            _, payload = mock_save.call_args[0]
                            assert payload["decision"] == "TRADE"
                            assert payload["dry_run"] is False
                            assert payload["forced"] is True
                            assert payload["orders"][0]["status"] == "FILLED"
