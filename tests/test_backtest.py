import numpy as np
import pandas as pd
import pytest

from hongstr.backtest.engine import BacktestEngine
from hongstr.semantics.core import SemanticsV1


@pytest.fixture
def synthetic_data():
    # Create 48 hours of data (hourly)
    idx = pd.date_range("2024-02-01 00:00:00", periods=48, freq="1h", tz="Asia/Taipei")
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
            return 'LONG'
        if strategy.count == 48:
            return 'FLAT'
        return None

    results = engine.run("BTCUSDT", strategy)

    # Baseline engine contract: result includes top-level metrics + trades.
    assert "metrics" in results
    assert "trades" in results
    assert len(results["trades"]) > 0
    assert results["metrics"]["trades_count"] > 0
    assert "start_equity" in results["metrics"]
    assert "end_equity" in results["metrics"]

    print("Backtest Results:", results["metrics"])
