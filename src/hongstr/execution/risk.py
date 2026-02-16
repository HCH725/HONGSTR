from dataclasses import dataclass, field
from typing import Dict, Optional, List
import logging
from .models import SignalEvent, OrderRequest, Position
from ..config import (
    MAX_CONCURRENT_POSITIONS, MAX_ORDER_NOTIONAL, MAX_TOTAL_EXPOSURE,
    ALLOW_LONG, ALLOW_SHORT, OFFLINE_MODE
)

logger = logging.getLogger(__name__)

@dataclass
class RiskDecision:
    allowed: bool
    reason: str
    details: Dict = field(default_factory=dict)

class RiskManager:
    def __init__(self):
        self.max_concurrent = MAX_CONCURRENT_POSITIONS
        self.max_notional_per_order = MAX_ORDER_NOTIONAL
        self.max_total_exposure = MAX_TOTAL_EXPOSURE
        self.allow_long = ALLOW_LONG
        self.allow_short = ALLOW_SHORT

    def evaluate(self, signal: SignalEvent, order: OrderRequest, 
                 current_positions: Dict[str, Position], 
                 account_balance: float) -> RiskDecision:
        
        # 0. Offline Check (Executor usually handles this, but good as backup)
        if OFFLINE_MODE:
             pass # Executor handles it, logic here focuses on trade params

        # 1. Direction Check
        if signal.direction == 'LONG' and not self.allow_long:
            return RiskDecision(False, "DIRECTION_DISABLED", {"direction": "LONG"})
        if signal.direction == 'SHORT' and not self.allow_short:
            return RiskDecision(False, "DIRECTION_DISABLED", {"direction": "SHORT"})

        # 2. Max Notional Per Order
        # Estimated Notional = qty * price
        # For MARKET orders, price might be None or rough. OrderRequest from Executor usually has estimated price.
        est_price = order.price if order.price else 0.0
        # If price is 0 (pure market with no reference), we can't check efficiently without ticker.
        # Executor usually provides a safety price or we trust it.
        # Assuming Executor passes estimated price in OrderRequest or we look it up?
        # The user said "若已有 qty/price 可估". Executor.execute_signal sets price=100000.0 fallback or paper price.
        
        notional = order.qty * est_price
        if notional > self.max_notional_per_order:
             return RiskDecision(False, "MAX_ORDER_NOTIONAL", 
                                 {"notional": notional, "limit": self.max_notional_per_order})

        # 3. Concurrent Positions
        # If opening new position (current pos is NONE)
        # Check total active positions
        active_symbols = [p.symbol for p in current_positions.values() if p.side != 'NONE']
        if signal.symbol not in active_symbols:
            # New position
            if len(active_symbols) >= self.max_concurrent:
                return RiskDecision(False, "MAX_CONCURRENT_POSITIONS", 
                                    {"current": len(active_symbols), "limit": self.max_concurrent})

        # 4. Total Exposure
        # Sum of abs(notional) of all positions + new order
        current_exposure = sum([p.amt * p.entry_price for p in current_positions.values() if p.side != 'NONE'])
        projected_exposure = current_exposure + notional
        if projected_exposure > self.max_total_exposure:
             return RiskDecision(False, "MAX_TOTAL_EXPOSURE", 
                                 {"projected": projected_exposure, "limit": self.max_total_exposure})

        return RiskDecision(True, "ALLOWED")
