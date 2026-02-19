import pandas as pd

from hongstr.signal.indicators import ema, rsi, sma, supertrend, vwap_session


def test_indicators_basic():
    # Simple data
    data = pd.Series([10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10])

    # SMA
    s = sma(data, 3)
    assert pd.isna(s[1])
    assert s[2] == (10 + 11 + 12) / 3

    # EMA coverage
    e = ema(data, 3)
    assert not pd.isna(e[0])

    # RSI
    # Needs more data to stabilize
    prices = pd.Series([100] * 20 + [110, 120, 130])  # Flat then rise
    r = rsi(prices, 14)
    assert r.iloc[-1] > 50


def test_supertrend_logic():
    # Synthetic data: Flat then rise then fall
    # 20 bars
    closes = [100] * 5 + [101, 102, 103, 104, 105, 106] + [105, 104, 100, 90, 80]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]

    df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
    dir_s, band_s = supertrend(
        df["high"], df["low"], df["close"], period=5, multiplier=1.0
    )

    # Expect flip to 1 during rise
    assert dir_s.iloc[8] == 1
    # Expect flip to -1 during fall
    assert dir_s.iloc[-1] == -1


def test_vwap():
    # 3 bars same day
    h = pd.Series([10, 20, 30])
    l = pd.Series([10, 20, 30])
    c = pd.Series([10, 20, 30])  # Typ = 10, 20, 30
    v = pd.Series([100, 100, 100])
    t = pd.Series(
        pd.to_datetime(["2024-01-01 10:00", "2024-01-01 11:00", "2024-01-01 12:00"])
    )

    vwp = vwap_session(h, l, c, v, t)
    # Bar 1: PV=1000, V=100 => 10
    # Bar 2: PV=2000, V=100. CumPV=3000, CumV=200 => 15
    # Bar 3: PV=3000, V=100. CumPV=6000, CumV=300 => 20
    assert vwp[0] == 10.0
    assert vwp[1] == 15.0
    assert vwp[2] == 20.0
