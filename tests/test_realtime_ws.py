from hongstr.realtime.binance_ws import build_stream_url, parse_aggtrade, parse_kline
from hongstr.realtime.types import AggTradeEvent, KlineEvent


def test_build_stream_url():
    base_url = "wss://stream.binance.com:9443/stream"
    symbols = ["BTCUSDT", "ETHUSDT"]
    streams = ["aggTrade", "kline_1m"]

    url = build_stream_url(base_url, symbols, streams)

    expected_streams = (
        "btcusdt@aggTrade/btcusdt@kline_1m/ethusdt@aggTrade/ethusdt@kline_1m"
    )
    expected_url = f"{base_url}?streams={expected_streams}"

    assert url == expected_url


def test_parse_aggtrade():
    payload = {
        "e": "aggTrade",
        "E": 123456789,
        "s": "BNBBTC",
        "a": 12345,
        "p": "0.001",
        "q": "100",
        "f": 100,
        "l": 105,
        "T": 123456785,
        "m": True,
        "M": True,
    }

    event = parse_aggtrade(payload)

    assert isinstance(event, AggTradeEvent)
    assert event.symbol == "BNBBTC"
    assert event.price == 0.001
    assert event.quantity == 100.0
    assert event.is_buyer_maker is True
    assert event.event_time == 123456789


def test_parse_kline():
    payload = {
        "e": "kline",
        "E": 123456789,
        "s": "BNBBTC",
        "k": {
            "t": 123400000,
            "T": 123460000,
            "s": "BNBBTC",
            "i": "1m",
            "f": 100,
            "L": 200,
            "o": "0.0010",
            "c": "0.0020",
            "h": "0.0025",
            "l": "0.0015",
            "v": "1000",
            "n": 100,
            "x": False,
            "q": "1.0000",
            "V": "500",
            "Q": "0.500",
            "B": "123456",
        },
    }

    event = parse_kline(payload)

    assert isinstance(event, KlineEvent)
    assert event.symbol == "BNBBTC"
    assert event.kline.interval == "1m"
    assert event.kline.open_price == 0.0010
    assert event.kline.close_price == 0.0020
    assert event.kline.high_price == 0.0025
    assert event.kline.low_price == 0.0015
    assert event.kline.is_closed is False
