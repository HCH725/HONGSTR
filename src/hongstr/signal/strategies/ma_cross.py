from typing import List, Optional
import pandas as pd
from ..types import Bar, SignalEvent
from .base import BaseStrategy

class MACrossStrategy(BaseStrategy):
    def __init__(self, strategy_id: str, fast_period: int = 10, slow_period: int = 20):
        super().__init__(strategy_id)
        self.fast_period = fast_period
        self.slow_period = slow_period
        
    @property
    def required_timeframes(self) -> List[str]:
        return ["1m", "5m", "15m", "1h", "4h"] # Supports any
        
    def on_bars(self, symbol: str, timeframe: str, bars: List[Bar]) -> Optional[SignalEvent]:
        if len(bars) < self.slow_period + 1:
            return None
            
        # Extract closes
        closes = pd.Series([b.close for b in bars])
        
        fast_ma = closes.rolling(window=self.fast_period).mean()
        slow_ma = closes.rolling(window=self.slow_period).mean()
        
        # Check crossover at the last bar (index -1)
        # We need check if cross happened exactly now:
        # fast[-1] > slow[-1] AND fast[-2] <= slow[-2] => LONG
        # fast[-1] < slow[-1] AND fast[-2] >= slow[-2] => SHORT
        
        curr_fast = fast_ma.iloc[-1]
        curr_slow = slow_ma.iloc[-1]
        prev_fast = fast_ma.iloc[-2]
        prev_slow = slow_ma.iloc[-2]
        
        direction = "FLAT"
        reason = ""
        
        if curr_fast > curr_slow and prev_fast <= prev_slow:
            direction = "LONG"
            reason = f"Golden Cross {self.fast_period}/{self.slow_period} ({curr_fast:.2f} > {curr_slow:.2f})"
        elif curr_fast < curr_slow and prev_fast >= prev_slow:
            direction = "SHORT"
            reason = f"Death Cross {self.fast_period}/{self.slow_period} ({curr_fast:.2f} < {curr_slow:.2f})"
            
        if direction != "FLAT":
            return SignalEvent(
                ts=bars[-1].ts,
                symbol=symbol,
                portfolio_id="HONG", # Default
                strategy_id=self.strategy_id,
                direction=direction,
                timeframe=timeframe,
                reason=reason
            )
            
        return None
