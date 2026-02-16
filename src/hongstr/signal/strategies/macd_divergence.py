from typing import List, Set, Optional
import pandas as pd
from ..types import Bar, SignalEvent
from .base import BaseStrategy
from ..indicators import ema
from ...config import (
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    DVG_LOOKBACK, DVG_PIVOT_LEFT, DVG_PIVOT_RIGHT,
    STRATEGY_TIMEFRAME_SIGNAL
)

class MACDDivergenceStrategy(BaseStrategy):
    def __init__(self, strategy_id: str = "macd_divergence"):
        super().__init__(strategy_id)
        self.signal_tf = STRATEGY_TIMEFRAME_SIGNAL

    @property
    def required_timeframes(self) -> Set[str]:
        return {self.signal_tf}

    def on_bars(self, symbol: str, timeframe: str, bars: List[Bar]) -> Optional[SignalEvent]:
        if timeframe != self.signal_tf:
            return None
        
        min_bars = MACD_SLOW + MACD_SIGNAL + DVG_LOOKBACK + 10
        if len(bars) < min_bars:
            return None

        df = pd.DataFrame([b.__dict__ for b in bars])
        closes = df['close']
        
        # 1. Calc MACD
        fast_ema = ema(closes, MACD_FAST)
        slow_ema = ema(closes, MACD_SLOW)
        macd_line = fast_ema - slow_ema
        # We use MACD Line (not histogram) for divergence typically, or Histogram.
        # Let's use MACD Line (Trend oscillator).
        oscillator = macd_line
        
        # 2. Pivot Logic (Same as RSI)
        curr_idx = len(closes) - 1
        pivot_idx = curr_idx - DVG_PIVOT_RIGHT
        
        if pivot_idx < DVG_PIVOT_LEFT:
            return None
            
        def is_pivot_low(series, idx):
            window = series.iloc[idx-DVG_PIVOT_LEFT : idx+DVG_PIVOT_RIGHT+1]
            if len(window) < DVG_PIVOT_LEFT + DVG_PIVOT_RIGHT + 1: return False
            return series.iloc[idx] == window.min()

        def is_pivot_high(series, idx):
            window = series.iloc[idx-DVG_PIVOT_LEFT : idx+DVG_PIVOT_RIGHT+1]
            if len(window) < DVG_PIVOT_LEFT + DVG_PIVOT_RIGHT + 1: return False
            return series.iloc[idx] == window.max()
            
        signal_side = None
        
        # Note: Pivot check needs to be on PRICE pivots primarily, divergent with OSC pivots?
        # Standard: Price makes LL, Oscillator makes HL.
        # So check Price Pivots.
        
        # Bullish Div
        if is_pivot_low(closes, pivot_idx):
            curr_price_low = closes.iloc[pivot_idx]
            curr_osc_val = oscillator.iloc[pivot_idx]
            
            for i in range(1, DVG_LOOKBACK):
                prev_p_idx = pivot_idx - i
                if prev_p_idx < DVG_PIVOT_LEFT: break
                
                if is_pivot_low(closes, prev_p_idx):
                    prev_price_low = closes.iloc[prev_p_idx]
                    prev_osc_val = oscillator.iloc[prev_p_idx]
                    
                    if curr_price_low < prev_price_low and curr_osc_val > prev_osc_val:
                        signal_side = "LONG"
                        break
                        
        # Bearish Div
        if not signal_side and is_pivot_high(closes, pivot_idx):
            curr_price_high = closes.iloc[pivot_idx]
            curr_osc_val = oscillator.iloc[pivot_idx]
            
            for i in range(1, DVG_LOOKBACK):
                prev_p_idx = pivot_idx - i
                if prev_p_idx < DVG_PIVOT_LEFT: break
                
                if is_pivot_high(closes, prev_p_idx):
                    prev_price_high = closes.iloc[prev_p_idx]
                    prev_osc_val = oscillator.iloc[prev_p_idx]
                    
                    if curr_price_high > prev_price_high and curr_osc_val < prev_osc_val:
                        signal_side = "SHORT"
                        break
        
        if signal_side:
            return SignalEvent(
                ts=bars[-1].ts,
                symbol=symbol,
                portfolio_id="HONG",
                strategy_id=self.strategy_id,
                direction=signal_side,
                timeframe=timeframe,
                regime="REVERSAL",
                confidence=0.85
            )
            
        return None
