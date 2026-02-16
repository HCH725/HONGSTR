import pytest
from datetime import datetime
import pytz
import pandas as pd

def test_timezone_conversion_alignment():
    # Test that converting a typical 1m timestamp from UTC to Asia/Taipei preserves minute alignment
    # 2020-01-01 00:00:00 UTC -> 2020-01-01 08:00:00 Asia/Taipei
    
    ts_utc = pd.Timestamp("2020-01-01 00:00:00")
    tz = pytz.timezone("Asia/Taipei")
    
    # If purely naive, localize to UTC first
    ts_utc_localized = ts_utc.tz_localize("UTC")
    ts_local = ts_utc_localized.tz_convert(tz)
    
    assert ts_local.year == 2020
    assert ts_local.month == 1
    assert ts_local.day == 1
    assert ts_local.hour == 8
    assert ts_local.minute == 0
    assert ts_local.second == 0
    
def test_binance_start_alignment():
    # Spec start: 2020-01-01 00:00:00 GMT+8
    # Should be 2019-12-31 16:00:00 UTC
    
    target_local_str = "2020-01-01 00:00:00"
    tz = pytz.timezone("Asia/Taipei")
    
    # Naive string -> local aware
    dt_naive = datetime.strptime(target_local_str, "%Y-%m-%d %H:%M:%S")
    dt_local = tz.localize(dt_naive)
    
    # Convert to UTC
    dt_utc = dt_local.astimezone(pytz.UTC)
    
    assert dt_utc.year == 2019
    assert dt_utc.month == 12
    assert dt_utc.day == 31
    assert dt_utc.hour == 16
    assert dt_utc.minute == 0
