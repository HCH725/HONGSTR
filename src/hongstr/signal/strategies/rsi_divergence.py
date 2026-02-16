from typing import List, Set, Optional
import pandas as pd
import numpy as np
from ..types import Bar, SignalEvent
from .base import BaseStrategy
from ..indicators import rsi
from ...config import (
    RSI_PERIOD, DVG_LOOKBACK, DVG_PIVOT_LEFT, DVG_PIVOT_RIGHT,
    STRATEGY_TIMEFRAME_SIGNAL
)

class RSIDivergenceStrategy(BaseStrategy):
    def __init__(self, strategy_id: str = "rsi_divergence"):
        super().__init__(strategy_id)
        self.signal_tf = STRATEGY_TIMEFRAME_SIGNAL

    @property
    def required_timeframes(self) -> Set[str]:
        return {self.signal_tf}

    def on_bars(self, symbol: str, timeframe: str, bars: List[Bar]) -> Optional[SignalEvent]:
        if timeframe != self.signal_tf:
            return None
        
        # Need enough bars for RSI + pivots + lookback
        min_bars = RSI_PERIOD + DVG_LOOKBACK + 10
        if len(bars) < min_bars:
            return None

        df = pd.DataFrame([b.__dict__ for b in bars])
        closes = df['close']
        
        # 1. Calc RSI
        rsi_series = rsi(closes, RSI_PERIOD)
        
        # 2. Identify Pivots (check if T-right was a pivot)
        # We only care about the pivot that was CONFIRMED at the current bar (T).
        # A pivot at index P is confirmed at index P + right.
        # So we check if index (len-1) - right was a pivot.
        
        curr_idx = len(closes) - 1
        pivot_idx = curr_idx - DVG_PIVOT_RIGHT
        
        if pivot_idx < DVG_PIVOT_LEFT:
            return None
            
        # Helper to check if idx is pivot low logic
        def is_pivot_low(series, idx):
            window = series.iloc[idx-DVG_PIVOT_LEFT : idx+DVG_PIVOT_RIGHT+1]
            if len(window) < DVG_PIVOT_LEFT + DVG_PIVOT_RIGHT + 1:
                return False
            return series.iloc[idx] == window.min()

        def is_pivot_high(series, idx):
            window = series.iloc[idx-DVG_PIVOT_LEFT : idx+DVG_PIVOT_RIGHT+1]
            if len(window) < DVG_PIVOT_LEFT + DVG_PIVOT_RIGHT + 1:
                return False
            return series.iloc[idx] == window.max()
            
        signal_side = None
        
        # Check Bullish Divergence (Pivot Lows)
        # 1. Check if pivot_idx is a pivot low in PRICE and RSI (often just Price pivot is enough, 
        #    but usually we look for price LL and RSI HL).
        #    Strict definition: Price makes pivot low, RSI *correspondingly* is higher than previous RSI pivot low.
        
        if is_pivot_low(closes, pivot_idx):
            # Price pivot low confirmed.
            # Look back for previous pivot low in PRICE within lookback window
            curr_price_low = closes.iloc[pivot_idx]
            curr_rsi_val = rsi_series.iloc[pivot_idx]
            
            # Search backwards for prior pivot low
            found_prev = False
            for i in range(1, DVG_LOOKBACK):
                prev_p_idx = pivot_idx - i
                if prev_p_idx < DVG_PIVOT_LEFT:
                    break
                
                if is_pivot_low(closes, prev_p_idx):
                    # Found previous pivot low
                    prev_price_low = closes.iloc[prev_p_idx]
                    prev_rsi_val = rsi_series.iloc[prev_p_idx]
                    
                    # Bullish Div: Price Lower Low, RSI Higher Low
                    if curr_price_low < prev_price_low and curr_rsi_val > prev_rsi_val:
                        # Found it!
                        signal_side = "LONG"
                        found_prev = True
                        break # Only trigger on most recent valid divergence
            
        # Check Bearish Divergence (Pivot Highs)
        if not signal_side and is_pivot_high(closes, pivot_idx):
            curr_price_high = closes.iloc[pivot_idx]
            curr_rsi_val = rsi_series.iloc[pivot_idx]
            
            for i in range(1, DVG_LOOKBACK):
                prev_p_idx = pivot_idx - i
                if prev_p_idx < DVG_PIVOT_LEFT:
                    break
                    
                if is_pivot_high(closes, prev_p_idx):
                    prev_price_high = closes.iloc[prev_p_idx]
                    prev_rsi_val = rsi_series.iloc[prev_p_idx]
                    
                    # Bearish Div: Price Higher High, RSI Lower High
                    if curr_price_high > prev_price_high and curr_rsi_val < prev_rsi_val:
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
                confidence=0.8
            )
            
        return None
