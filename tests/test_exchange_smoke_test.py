import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts to path
sys.path.append(str(Path(__file__).parent.parent))
from scripts.exchange_smoke_test import main


def run_main():
    with patch.object(sys, "argv", ["exchange_smoke_test.py"]):
        return main()


def test_missing_env_vars():
    """Missing keys should degrade to WARN for GET_ACCOUNT mode."""
    with patch.dict(os.environ, {}, clear=True):
        assert run_main() == 2

def test_testnet_mode_detection():
    """Test that base_url is set correctly based on env."""
    with patch.dict(os.environ, {
        "BINANCE_API_KEY": "mock_key",
        "BINANCE_API_SECRET": "mock_secret",
        "BINANCE_FUTURES_TESTNET": "1"
    }):
        with patch("scripts.exchange_smoke_test.requests.request") as mock_request:
            mock_request.return_value = MagicMock(status_code=200, json=lambda: {"availableBalance": "1"})
            with patch("scripts.exchange_smoke_test.build_signed_request") as mock_req:
                mock_req.return_value = ("http://testnet.binancefuture.com/fapi/v2/account", {}, None)
                assert run_main() == 0
                args, _ = mock_req.call_args
                assert "testnet.binancefuture.com" in args[1]

def test_production_mode_detection():
    """Test that base_url defaults to production."""
    with patch.dict(os.environ, {
        "BINANCE_API_KEY": "mock_key",
        "BINANCE_API_SECRET": "mock_secret",
        "BINANCE_FUTURES_TESTNET": "0"
    }):
        with patch("scripts.exchange_smoke_test.requests.request") as mock_request:
            mock_request.return_value = MagicMock(status_code=200, json=lambda: {"availableBalance": "1"})
            with patch("scripts.exchange_smoke_test.build_signed_request") as mock_req:
                mock_req.return_value = ("http://fapi.binance.com/fapi/v2/account", {}, None)
                assert run_main() == 0
                args, _ = mock_req.call_args
                assert "fapi.binance.com" in args[1]
