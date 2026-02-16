from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class SemanticsV1:
    """
    Single Source of Truth for Backtest Semantics (Version 1.0.0).
    Handles Fees, Slippage, Funding, and Rules.
    """
    version: str = "1.0.0"
    
    # Fees (Taker only for V1 simplicity)
    taker_fee_rate: float = 0.0004  # 4 bps default (Binance VIP0)
    
    # Slippage (Fixed bps for V1)
    slippage_bps: float = 2.0       # 2 bps default
    
    # Funding Config
    funding_interval_hours: int = 8
    funding_hours_utc: list = field(default_factory=lambda: [0, 8, 16])
    
    # Exchange Rules
    min_notional: float = 5.0

    def is_funding_timestamp(self, ts) -> bool:
        """
        Check if timestamp (aware or naive assumed UTC) matches funding schedule.
        Binance Funding Times: 00:00, 08:00, 16:00 UTC.
        """
        if ts.tzinfo is None:
            # Assume UTC if naive, or strictly require aware?
            # Let's localize to UTC for safety check
            ts_utc = ts.tz_localize('UTC')
        else:
            ts_utc = ts.tz_convert('UTC')
            
        return ts_utc.hour in self.funding_hours_utc and ts_utc.minute == 0
    
    def apply_slippage(self, price: float, side: str, volume: float = 0) -> float:
        """
        Apply slippage to price.
        Buy: Price increases. Sell: Price decreases.
        """
        impact = price * (self.slippage_bps / 10000.0)
        if side.upper() == 'BUY':
            return price + impact
        elif side.upper() == 'SELL':
            return price - impact
        return price

    def calc_fee(self, notional: float) -> float:
        """Calculate taker fee on notional value."""
        return abs(notional) * self.taker_fee_rate

    def calc_funding(self, position_notional: float, funding_rate: float) -> float:
        """
        Calculate funding payment.
        Positive funding rate: Longs pay Shorts.
        - If Long (+notional): Pay (negative PnL) -> notional * rate
        - If Short (-notional): Receive (positive PnL) -> notional * rate (double negative = positive)
        
        Wait, standard formula:
        Funding Cost = Position Size * Funding Rate
        If Rate > 0:
           Long (Size > 0) pays: Cost > 0 (We want PnL impact, so should deduct)
           Short (Size < 0) receives: Cost < 0 (We want PnL impact, so should add)
           
        PnL Impact = - (Position Size * Funding Rate)
        """
        return -1.0 * position_notional * funding_rate

    def explain(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "taker_fee_rate": self.taker_fee_rate,
            "slippage_bps": self.slippage_bps,
            "funding_interval_hours": self.funding_interval_hours,
            "min_notional": self.min_notional
        }
