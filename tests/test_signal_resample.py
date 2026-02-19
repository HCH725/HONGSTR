import pandas as pd

from hongstr.signal.resample import resample_bars
from hongstr.signal.types import Bar


def test_resample_1m_to_5m():
    # Create 5 1m bars
    bars = []
    base_ts = pd.Timestamp("2024-01-01 10:00:00")
    for i in range(5):
        bars.append(Bar(
            ts=base_ts + pd.Timedelta(minutes=i),
            symbol="BTCUSDT",
            open=100 + i,
            high=105 + i,
            low=95 + i,
            close=102 + i,
            volume=10,
            closed=True
        ))

    # Resample to 5m
    # The 5m bar starts at 10:00 and ends at 10:05.
    # We have data for 10:00, 01, 02, 03, 04.
    # The last bar ts is 10:04.
    # logic: is_closed = last_1m_ts >= bar_end (10:05) -> False.
    # So with 5 bars [00, 01, 02, 03, 04], we haven't seen >= 10:05.
    # The bar [10:00, 10:05) is NOT closed yet.

    resampled = resample_bars(bars, "5m")
    assert len(resampled) == 0

    # Add one more bar at 10:05
    bars.append(Bar(
        ts=base_ts + pd.Timedelta(minutes=5),
        symbol="BTCUSDT",
        open=110, high=115, low=105, close=112, volume=10, closed=True
    ))

    resampled = resample_bars(bars, "5m")
    assert len(resampled) == 1

    b = resampled[0]
    assert b.ts == base_ts
    assert b.open == 100
    assert b.high == 109 # 105+4
    assert b.low == 95   # 95+0
    assert b.close == 106 # 102+4 (last in window)
    assert b.volume == 50

def test_resample_1m_to_1h():
    bars = []
    base_ts = pd.Timestamp("2024-01-01 10:00:00")
    for i in range(60):
        bars.append(Bar(
            ts=base_ts + pd.Timedelta(minutes=i),
            symbol="BTCUSDT",
            open=100, high=100, low=100, close=100, volume=1, closed=True
        ))

    # Last bar is 10:59.
    # 1h bar ends at 11:00.
    # 10:59 < 11:00 -> not closed.
    resampled = resample_bars(bars, "1h")
    assert len(resampled) == 0

    # Add 11:00 bar
    bars.append(Bar(
        ts=base_ts + pd.Timedelta(hours=1),
        symbol="BTCUSDT",
        open=100, high=100, low=100, close=100, volume=1, closed=True
    ))

    resampled = resample_bars(bars, "1h")
    assert len(resampled) == 1
    assert resampled[0].volume == 60
