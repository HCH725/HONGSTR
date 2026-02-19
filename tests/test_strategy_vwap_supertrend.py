import pandas as pd

from hongstr.signal.strategies.vwap_supertrend import VWAPSupertrendStrategy
from hongstr.signal.types import Bar


def test_vwap_supertrend_trigger():
    strat = VWAPSupertrendStrategy()

    # Construct bars where Supertrend flips UP and Price > VWAP
    # We need enough bars for ST warmup (ATR period=10 typically)
    base_ts = pd.Timestamp("2024-01-01 10:00:00")
    bars = []

    # 20 bars flat at 100
    for i in range(20):
        bars.append(Bar(base_ts + pd.Timedelta(hours=i), "BTC", 100, 101, 99, 100, 100, True))

    # Bar 21: Huge pump -> Price > VWAP and ST Up
    bars.append(Bar(base_ts + pd.Timedelta(hours=20), "BTC", 110, 115, 105, 112, 1000, True))

    # Run
    # ST period is 10. 20 bars history is enough.
    # At bar 20 (index 19), price 100.
    # At bar 21 (index 20), price 112.
    # VWAP will drag up slowly (heavy volume on last bar though).
    # VWAP approx: (20*100*100 + 112*1000) / (2000+1000) ~ (200000+112000)/3000 = 104
    # Close 112 > VWAP 104.
    # Supertrend should flip up.

    sig = strat.on_bars("BTC", "1h", bars)
    assert sig is not None
    assert sig.direction == "LONG"
