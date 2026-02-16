import pytest
from hongstr.execution.exchange_filters import ExchangeFilters

def test_round_qty_step_001():
    filters = ExchangeFilters()
    filters.set_filters('BTCUSDT', 0.1, 0.001, 0.001, 5.0)
    
    # 0.1234 -> 0.123
    assert filters.round_qty('BTCUSDT', 0.1234) == 0.123
    # 0.1239 -> 0.123
    assert filters.round_qty('BTCUSDT', 0.1239) == 0.123

def test_round_qty_step_1():
    filters = ExchangeFilters()
    filters.set_filters('XRPUSDT', 0.0001, 1.0, 10.0, 5.0)
    
    assert filters.round_qty('XRPUSDT', 123.45) == 123.0

def test_round_price_tick():
    filters = ExchangeFilters()
    filters.set_filters('BTCUSDT', 0.1, 0.001, 0.001, 5.0)
    
    # 50000.05 -> 50000.1 (Nearest?) or 50000.0?
    # Code uses round(steps)*tick. round(x.5) is nearest even in Py3.
    # 50000.05 / 0.1 = 500000.5 -> 500000 -> 50000.0
    # 50000.06 / 0.1 = 500000.6 -> 500001 -> 50000.1
    # Check behavior.
    assert filters.round_price('BTCUSDT', 50000.04) == 50000.0
    assert filters.round_price('BTCUSDT', 50000.06) == 50000.1

def test_validations():
    filters = ExchangeFilters()
    filters.set_filters('BTCUSDT', 0.1, 0.001, 0.01, 10.0) # min_qty=0.01, min_notional=10
    
    ok, msg = filters.is_qty_valid('BTCUSDT', 0.005)
    assert not ok
    assert "QTY_TOO_SMALL" in msg
    
    ok, msg = filters.is_qty_valid('BTCUSDT', 0.02)
    assert ok
    
    ok, msg = filters.is_notional_valid('BTCUSDT', 100.0, 0.02) # 2.0 < 10.0
    assert not ok
    assert "NOTIONAL_TOO_SMALL" in msg
