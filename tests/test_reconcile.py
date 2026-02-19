import json
import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts to path
sys.path.append(str(Path(__file__).parent.parent))
from scripts.order_reconcile import main as reconcile_main


def test_reconcile_status_transition(tmp_path):
    """Test that reconcile updates status from NEW to FILLED."""
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    report_path = report_dir / "orders_latest.json"

    order_data = {
        "timestamp": "2024-01-01T00:00:00Z",
        "orders": [
            {
                "symbol": "BTCUSDT",
                "orderId": "12345",
                "status": "NEW",
                "avgPrice": "0",
                "executedQty": "0"
            }
        ]
    }
    with open(report_path, "w") as f:
        json.dump(order_data, f)

    mock_details = {
        "symbol": "BTCUSDT",
        "orderId": "12345",
        "status": "FILLED",
        "avgPrice": "50000.0",
        "executedQty": "0.1",
        "cumQuote": "5000.0",
        "updateTime": 123456789
    }

    with patch("scripts.order_reconcile.BinanceFuturesTestnetBroker") as mock_broker_cls:
        mock_instance = mock_broker_cls.return_value
        mock_instance.get_order.return_value = mock_details

        with patch("sys.argv", ["order_reconcile.py", "--report", str(report_path)]):
            reconcile_main()

    # Check updated JSON
    with open(report_path, "r") as f:
        updated_data = json.load(f)

    updated_order = updated_data["orders"][0]
    assert updated_order["status"] == "FILLED"
    assert updated_order["avgPrice"] == "50000.0"
    assert updated_order["executedQty"] == "0.1"

def test_reconcile_idempotency(tmp_path):
    """Test that reconcile does nothing if status is already FILLED."""
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    report_path = report_dir / "orders_latest.json"

    order_data = {
        "orders": [{"symbol": "BTCUSDT", "orderId": "12345", "status": "FILLED"}]
    }
    with open(report_path, "w") as f:
        json.dump(order_data, f)

    with patch("scripts.order_reconcile.BinanceFuturesTestnetBroker") as mock_broker_cls:
        mock_instance = mock_broker_cls.return_value

        with patch("sys.argv", ["order_reconcile.py", "--report", str(report_path)]):
            reconcile_main()

        # get_order should NOT be called for FILLED orders
        assert mock_instance.get_order.call_count == 0
