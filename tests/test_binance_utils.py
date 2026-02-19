import urllib.parse
from unittest.mock import MagicMock, patch

from hongstr.execution.binance_testnet import BinanceFuturesTestnetBroker
from hongstr.execution.binance_utils import build_signed_request
from hongstr.execution.models import OrderRequest


class _TestBinanceBroker(BinanceFuturesTestnetBroker):
    """Concrete test double for abstract broker contract."""

    def get_order(self, symbol, order_id=None, client_order_id=None):
        return {
            "symbol": symbol,
            "orderId": order_id,
            "clientOrderId": client_order_id,
        }


def test_build_signed_request_deterministic():
    """Verify that build_signed_request creates a deterministic URL and redacts secrets."""  # noqa: E501
    base = "https://test.com"
    path = "/v1/test"
    params = {"symbol": "BTCUSDT", "side": "BUY", "timestamp": 123456789}
    key = "my_api_key"
    secret = "my_secret"

    url, headers, debug = build_signed_request(
        "GET", base, path, params, key, secret, debug=True
    )

    # Check headers
    assert headers["X-MBX-APIKEY"] == key

    # Check URL structure
    parsed = urllib.parse.urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "test.com"
    assert parsed.path == path

    query = urllib.parse.parse_qs(parsed.query)
    assert query["symbol"][0] == "BTCUSDT"
    assert query["side"][0] == "BUY"
    assert query["timestamp"][0] == "123456789"
    assert "signature" in query
    assert len(query["signature"][0]) == 64

    # Check deterministic sorted pre-sign QS in debug
    assert "Pre-Sign QS:   side=BUY&symbol=BTCUSDT&timestamp=123456789" in debug

    # Check redaction and debug info
    assert "my_secret" not in debug
    assert "my_api_key" not in debug
    assert "my_... (10)" in debug
    assert "Signature:     " in debug
    assert "signature=" in debug
    assert "****" in debug
    assert "Sent Mode:     sent_with_final_url_only: true" in debug
    assert "Note: urlencode performed exactly once on sorted items." in debug


def test_signing_consistency():
    """Verify that the same params result in the same signature regardless of input order."""  # noqa: E501
    base = "https://test.com"
    path = "/v1/test"
    key = "key"
    secret = "secret"

    # Different dict order, same content
    params1 = {"a": "1", "b": "2", "timestamp": 100}
    params2 = {"timestamp": 100, "b": "2", "a": "1"}

    url1, _, _ = build_signed_request("GET", base, path, params1, key, secret)
    url2, _, _ = build_signed_request("GET", base, path, params2, key, secret)

    assert url1 == url2
    assert "a=1&b=2&timestamp=100" in url1


def test_broker_request_uses_signed_url_only():
    """Verify broker sends signed params via requests.post and does not send body/json."""  # noqa: E501
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "orderId": 123,
                "status": "FILLED",
                "avgPrice": "100.0",
                "executedQty": "0.01",
            },
        )
        broker = _TestBinanceBroker()
        broker.key = "mock_key"
        broker.secret = "mock_secret"
        broker._ensure_isolated_margin = lambda symbol: None
        broker.filters.round_qty = lambda symbol, qty: qty
        broker.filters.round_price = lambda symbol, price: price

        req = OrderRequest("BTCUSDT", "BUY", 0.01, "MARKET")
        broker.place_order(req)

        assert mock_post.called
        _, kwargs = mock_post.call_args
        assert "params" in kwargs
        assert kwargs["params"]["symbol"] == "BTCUSDT"
        assert "signature" in kwargs["params"]
        assert kwargs["params"]["timestamp"] is not None
        assert kwargs.get("data") is None
        assert kwargs.get("json") is None


def test_broker_request_has_empty_body():
    """Verify broker uses query params only (no body payload) for signed order requests."""  # noqa: E501
    broker = _TestBinanceBroker()
    broker.key = "key"
    broker.secret = "secret"

    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "orderId": 456,
                "status": "FILLED",
                "avgPrice": "100.0",
                "executedQty": "0.02",
            },
        )
        broker._ensure_isolated_margin = lambda symbol: None
        broker.filters.round_qty = lambda symbol, qty: qty
        broker.filters.round_price = lambda symbol, price: price

        req = OrderRequest("BTCUSDT", "BUY", 0.02, "MARKET")
        broker.place_order(req)

        _, kwargs = mock_post.call_args
        assert kwargs.get("data") is None
        assert kwargs.get("json") is None
