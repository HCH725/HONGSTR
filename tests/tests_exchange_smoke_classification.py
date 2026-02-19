import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

sys.path.append(str(Path(__file__).parent.parent))
from scripts.exchange_smoke_test import main


def run_smoke(args):
    with patch.object(sys, "argv", ["exchange_smoke_test.py", *args]):
        return main()


def test_missing_env_keys_classified():
    with patch.dict(os.environ, {}, clear=True):
        with patch("scripts.exchange_smoke_test.emit_result") as emit:
            with patch("scripts.exchange_smoke_test.requests.get") as req_get:
                with patch("scripts.exchange_smoke_test.requests.request") as req:
                    rc = run_smoke(["--mode", "GET_ACCOUNT"])
            assert rc == 0
            req_get.assert_not_called()
            req.assert_not_called()
            emit.assert_called_once()
            status, reason, *_ = emit.call_args[0]
            assert status == "SKIP"
            assert reason == "ENV_MISSING_KEYS"


def test_ssl_error_classified():
    with patch.dict(
        os.environ, {"BINANCE_API_KEY": "k", "BINANCE_API_SECRET": "s"}, clear=True
    ):
        with patch("scripts.exchange_smoke_test.build_signed_request") as signed:
            signed.return_value = ("https://fapi.binance.com/fapi/v2/account", {}, None)
            with patch("scripts.exchange_smoke_test.requests.request") as req:
                req.side_effect = requests.exceptions.SSLError("ssl failed")
                with patch("scripts.exchange_smoke_test.emit_result") as emit:
                    rc = run_smoke(["--mode", "GET_ACCOUNT"])
                    assert rc == 2
                    _, reason, *_ = emit.call_args[0]
                    assert reason == "SSL_ERROR"


def test_connection_error_classified():
    with patch("scripts.exchange_smoke_test.requests.get") as req:
        req.side_effect = requests.exceptions.ConnectionError("dns failed")
        with patch("scripts.exchange_smoke_test.emit_result") as emit:
            rc = run_smoke(["--mode", "TIME"])
            assert rc == 2
            _, reason, *_ = emit.call_args[0]
            assert reason == "NETWORK_ERROR"


def test_signature_mismatch_classified():
    with patch.dict(
        os.environ, {"BINANCE_API_KEY": "k", "BINANCE_API_SECRET": "s"}, clear=True
    ):
        with patch("scripts.exchange_smoke_test.build_signed_request") as signed:
            signed.return_value = ("https://fapi.binance.com/fapi/v2/account", {}, None)
            with patch("scripts.exchange_smoke_test.requests.request") as req:
                resp = MagicMock(status_code=400)
                resp.json.return_value = {
                    "code": -1022,
                    "msg": "Signature for this request is not valid.",
                }
                req.return_value = resp
                with patch("scripts.exchange_smoke_test.emit_result") as emit:
                    rc = run_smoke(["--mode", "GET_ACCOUNT"])
                    assert rc == 2
                    _, reason, *_ = emit.call_args[0]
                    assert reason == "SIGNATURE_MISMATCH"


def test_auth_rejected_classified():
    with patch.dict(
        os.environ, {"BINANCE_API_KEY": "k", "BINANCE_API_SECRET": "s"}, clear=True
    ):
        with patch("scripts.exchange_smoke_test.build_signed_request") as signed:
            signed.return_value = ("https://fapi.binance.com/fapi/v2/account", {}, None)
            with patch("scripts.exchange_smoke_test.requests.request") as req:
                resp = MagicMock(status_code=401)
                resp.json.return_value = {
                    "code": -2015,
                    "msg": "Invalid API-key, IP, or permissions.",
                }
                req.return_value = resp
                with patch("scripts.exchange_smoke_test.emit_result") as emit:
                    rc = run_smoke(["--mode", "GET_ACCOUNT"])
                    assert rc == 2
                    _, reason, *_ = emit.call_args[0]
                    assert reason == "AUTH_REJECTED"
