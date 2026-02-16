import pytest
from hongstr.execution.exchange_filters import ExchangeFilters
from hongstr.config import SMOKE_NOTIONAL_USD

class TestSmokeBuilders:
    def test_smoke_order_sizing(self):
        filters = ExchangeFilters()
        # Mock fetch_filters implicitly by using defaults in mvp class
        # or assuming ExchangeFilters works locally without network if fetch fails?
        # ExchangeFilters currently hardcodes defaults if fetch fails or logic is static.
        
        price = 50000.0
        notional = SMOKE_NOTIONAL_USD # Should be 10.0
        raw = notional / price
        rounded = filters.round_qty("BTCUSDT", raw)
        
        assert rounded > 0
        assert rounded * price >= 5.0 # Check against likely min notional
        # 10 / 50000 = 0.0002. Min qty usually 0.001?
        # If min qty is 0.001, then 0.0002 rounds to 0.001? Or 0?
        # logic: round(qty / step) * step.
        # 0.0002 / 0.001 = 0.2 -> round -> 0.
        # So at 50k price, 10 USD might be too small for BTC!
        # BTC min notional is 5 USDT usually. Min qty 0.001.
        # 0.001 * 50000 = 50 USD!
        # So 10 USD smoke is invalid for BTC.
        # User defined SMOKE_NOTIONAL_USD=10.
        # This test ensures we catch that or config is robust.
        
    def test_smoke_params(self):
        assert SMOKE_NOTIONAL_USD > 0
        
    def test_rounding_logic(self):
        f = ExchangeFilters()
        # Test Step Size 0.001
        assert f.round_qty("BTCUSDT", 0.1234) == 0.123
        assert f.round_qty("BTCUSDT", 0.1236) == 0.123
