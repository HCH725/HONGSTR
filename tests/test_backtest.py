import pytest
import pandas as pd
import numpy as np
import pytz
from hongstr.backtest.engine import BacktestEngine
from hongstr.semantics.core import SemanticsV1

@pytest.fixture
def synthetic_data():
    # Create 48 hours of data (hourly)
    idx = pd.date_range("2024-01-01 00:00:00", periods=48, freq="1h", tz="Asia/Taipei")
    df = pd.DataFrame({
        "open": np.linspace(100, 105, 48),
        "high": np.linspace(101, 106, 48),
        "low": np.linspace(99, 104, 48),
        "close": np.linspace(100.5, 105.5, 48),
        "volume": 1000
    }, index=idx)
    return df

def test_backtest_smoke(synthetic_data):
    sem = SemanticsV1()
    engine = BacktestEngine(sem, synthetic_data)
    
    # Simple Strategy: Buy on first candle, Exit on last
    def strategy(row):
        # We need a way to know index in this simple stub, but row is just series.
        # Stateful hack for test only
        if not hasattr(strategy, 'count'):
            strategy.count = 0
            
        strategy.count += 1
        if strategy.count == 1:
            return 'BUY'
        if strategy.count == 48:
            return 'EXIT'
        return None
        
    results = engine.run(strategy)
    
    assert results["semantics_version"] == "1.0.0"
    assert len(results["trades"]) > 0
    # Check OOS split
    # Data is 2024 -> Should be in OOS bucket
    assert "OOS" in results["splits"]
    assert results["splits"]["OOS"]["total_trades"] > 0
    assert results["splits"]["TRAIN"].get("total_trades", 0) == 0
    
    print("Backtest Results:", results["full_metrics"])
