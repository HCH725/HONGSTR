import math
from typing import Dict, Tuple

class ExchangeFilters:
    def __init__(self):
        # Cache for symbol -> filters
        # Format: {symbol: {'tick_size': float, 'step_size': float, 'min_qty': float, 'min_notional': float}}
        self._filters: Dict[str, Dict[str, float]] = {}
        
        # Hardcoded defaults for common pairs (MVP)
        # In real production, this should be fetched from exchangeInfo
        self._filters['BTCUSDT'] = {'tick_size': 0.1, 'step_size': 0.001, 'min_qty': 0.001, 'min_notional': 5.0}
        self._filters['ETHUSDT'] = {'tick_size': 0.01, 'step_size': 0.01, 'min_qty': 0.01, 'min_notional': 5.0}
        self._filters['BNBUSDT'] = {'tick_size': 0.01, 'step_size': 0.01, 'min_qty': 0.01, 'min_notional': 5.0}

    def set_filters(self, symbol: str, tick_size: float, step_size: float, min_qty: float, min_notional: float):
        self._filters[symbol] = {
            'tick_size': tick_size,
            'step_size': step_size,
            'min_qty': min_qty,
            'min_notional': min_notional
        }

    def get_filters(self, symbol: str) -> Dict[str, float]:
        return self._filters.get(symbol, {
            'tick_size': 0.01, 'step_size': 0.001, 'min_qty': 0.001, 'min_notional': 5.0
        })

    def round_qty(self, symbol: str, qty: float) -> float:
        """Round *down* to stepSize."""
        filters = self.get_filters(symbol)
        step = filters['step_size']
        if step == 0: return qty
        
        # Avoid float errors
        precision = int(round(-math.log(step, 10), 0))
        qty_str = "{:0.0{}f}".format(qty, precision) 
        # But this rounds nearest. We want floor for qty usually?
        # Standard approach: floor(qty / step) * step
        steps = math.floor(qty / step)
        rounded = steps * step
        return round(rounded, precision)

    def round_price(self, symbol: str, price: float) -> float:
        """Round to tickSize."""
        filters = self.get_filters(symbol)
        tick = filters['tick_size']
        if tick == 0: return price
        
        precision = int(round(-math.log(tick, 10), 0))
        # Price usually round half up or nearest
        steps = round(price / tick)
        rounded = steps * tick
        return round(rounded, precision)

    def is_qty_valid(self, symbol: str, qty: float) -> Tuple[bool, str]:
        filters = self.get_filters(symbol)
        if qty < filters['min_qty']:
            return False, f"QTY_TOO_SMALL (min: {filters['min_qty']})"
        return True, "OK"

    def is_notional_valid(self, symbol: str, price: float, qty: float) -> Tuple[bool, str]:
        filters = self.get_filters(symbol)
        notional = price * qty
        if notional < filters['min_notional']:
            return False, f"NOTIONAL_TOO_SMALL (min: {filters['min_notional']})"
        return True, "OK"
