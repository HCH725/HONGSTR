import pandas as pd
import pytest

from hongstr.execution.models import OrderRequest, Position, SignalEvent
from hongstr.execution.risk import RiskManager


@pytest.fixture
def risk_manager():
    return RiskManager()


def test_allow_long_enabled(risk_manager):
    # Setup
    risk_manager.allow_long = True
    sig = SignalEvent(
        ts=pd.Timestamp.now(),
        symbol="BTCUSDT",
        portfolio_id="HONG",
        strategy_id="test",
        direction="LONG",
        timeframe="1h",
        regime="TREND",
    )
    req = OrderRequest(
        symbol="BTCUSDT",
        side="BUY",
        qty=0.1,
        order_type="MARKET",
        price=50000.0,
        extra={},
    )

    # Exec
    res = risk_manager.evaluate(sig, req, {}, 100000.0)

    # Assert
    assert res.allowed is True
    assert res.reason == "ALLOWED"


def test_max_notional_rejection(risk_manager):
    risk_manager.max_notional_per_order = 1000.0
    sig = SignalEvent(
        ts=pd.Timestamp.now(),
        symbol="BTCUSDT",
        portfolio_id="HONG",
        strategy_id="test",
        direction="LONG",
        timeframe="1h",
        regime="TREND",
    )
    # 1.0 * 50000 = 50000 > 1000
    req = OrderRequest(
        symbol="BTCUSDT",
        side="BUY",
        qty=1.0,
        order_type="MARKET",
        price=50000.0,
        extra={},
    )

    res = risk_manager.evaluate(sig, req, {}, 100000.0)
    assert res.allowed is False
    assert res.reason == "MAX_ORDER_NOTIONAL"


def test_concurrent_positions_rejection(risk_manager):
    risk_manager.max_concurrent = 1
    # Existing position
    # Inferring Position signature from logs: symbol, side, amt, entry_price
    # Log: Position(symbol='BTCUSDT', side='LONG', amt=0.1, entry_price=100000.0, ...)
    # If partial args fail, we will fix.
    positions = {
        "ETHUSDT": Position(symbol="ETHUSDT", side="LONG", amt=1.0, entry_price=3000.0)
    }

    sig = SignalEvent(
        ts=pd.Timestamp.now(),
        symbol="BTCUSDT",
        portfolio_id="HONG",
        strategy_id="test",
        direction="LONG",
        timeframe="1h",
        regime="TREND",
    )
    req = OrderRequest(
        symbol="BTCUSDT",
        side="BUY",
        qty=0.1,
        order_type="MARKET",
        price=50000.0,
        extra={},
    )

    res = risk_manager.evaluate(sig, req, positions, 100000.0)
    assert res.allowed is False
    assert res.reason == "MAX_CONCURRENT_POSITIONS"


def test_direction_disabled_short(risk_manager):
    risk_manager.allow_short = False
    sig = SignalEvent(
        ts=pd.Timestamp.now(),
        symbol="BTCUSDT",
        portfolio_id="HONG",
        strategy_id="test",
        direction="SHORT",
        timeframe="1h",
        regime="TREND",
    )
    req = OrderRequest(
        symbol="BTCUSDT",
        side="SELL",
        qty=0.1,
        order_type="MARKET",
        price=50000.0,
        extra={},
    )

    res = risk_manager.evaluate(sig, req, {}, 100000.0)
    assert res.allowed is False
    assert res.reason == "DIRECTION_DISABLED"
