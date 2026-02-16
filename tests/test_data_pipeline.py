import pytest
import pandas as pd
import numpy as np
from hongstr.data.aggregate import resample_klines
from hongstr.data.quality import report_metrics

@pytest.fixture
def mock_1m_data():
    # 2 hours of data (120 min)
    idx = pd.date_range("2024-01-01 00:00:00", periods=120, freq="1min")
    df = pd.DataFrame({
        "open": np.arange(120),
        "high": np.arange(120) + 1,
        "low": np.arange(120) - 1,
        "close": np.arange(120) + 0.5,
        "volume": np.ones(120) * 100
    }, index=idx)
    return df

def test_aggregation_1h(mock_1m_data):
    # Aggregate to 1h. Should produce 2 rows (00:00, 01:00)
    res = resample_klines(mock_1m_data, "1h")
    assert len(res) == 2
    
    # Check first row (0-59 mins)
    # Open = first (0)
    # High = max (0..59 + 1 -> 60)
    # Low = min (0..59 - 1 -> -1)
    # Close = last (59.5)
    # Volume = sum (60 * 100 = 6000)
    
    row0 = res.iloc[0]
    assert row0["open"] == 0
    assert row0["high"] == 60
    assert row0["low"] == -1
    assert row0["close"] == 59.5
    assert row0["volume"] == 6000

def test_missing_data_quality():
    # Create data with gap
    idx1 = pd.date_range("2024-01-01 00:00:00", periods=10, freq="1min")
    idx2 = pd.date_range("2024-01-01 00:20:00", periods=10, freq="1min")
    df = pd.DataFrame(index=idx1.append(idx2)) # Gap of 10 mins (00:10..00:19)
    df["close"] = 1.0 # dummy
    
    # Expected: 20 rows. Total range 00:00 to 00:29 (30 mins).
    # Missing: 10 mins.
    
    metrics = report_metrics(df, "1m")
    assert metrics["total_expected"] == 30
    assert metrics["actual"] == 20
    assert metrics["missing_count"] == 10
    assert metrics["missing_ratio"] == 10/30
