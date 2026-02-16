from typing import List, Set, Optional
import pandas as pd
from ..types import Bar, SignalEvent
from .base import BaseStrategy
from ..indicators import supertrend, vwap_session
from ...config import (
    ST_ATR_PERIOD, ST_ATR_MULT, VWAP_ANCHOR, VWAP_BAND_STD,
    STRATEGY_TIMEFRAME_BASE, STRATEGY_TIMEFRAME_SIGNAL
)

class VWAPSupertrendStrategy(BaseStrategy):
    def __init__(self, strategy_id: str = "vwap_supertrend"):
        super().__init__(strategy_id)
        # We need 1m for VWAP accuracy, and signal timeframe (e.g. 1h) for Supertrend logic?
        # Or do we calc Supertrend ON the signal timeframe? Usually ST is on signal TF.
        # But VWAP is usually aggregated from 1m up to current time.
        # For simplicity in Phase 1: We'll compute ST on the 'bars' passed (which are resampled, e.g. 1h).
        # And we'll compute VWAP on these bars too for approximation, OR we assume 'bars' are 1m and we resample inside?
        # The Engine calls on_bars(tf, bars). If TF=1h, bars are 1h bars.
        
        self.signal_tf = STRATEGY_TIMEFRAME_SIGNAL
        self._prev_st_dir = {} # symbol -> 1 or -1

    @property
    def required_timeframes(self) -> Set[str]:
        return {self.signal_tf}

    def on_bars(self, symbol: str, timeframe: str, bars: List[Bar]) -> Optional[SignalEvent]:
        if timeframe != self.signal_tf:
            return None
            
        if len(bars) < ST_ATR_PERIOD + 10:
            return None

        # Convert to DataFrame
        df = pd.DataFrame([b.__dict__ for b in bars])
        df['ts'] = pd.to_datetime(df['ts'])
        df.set_index('ts', inplace=True)
        
        # Calculate Indicators
        # Supertrend
        st_dir, st_val = supertrend(df['high'], df['low'], df['close'], ST_ATR_PERIOD, ST_ATR_MULT)
        
        # VWAP (Approximation: on signal TF bars, still decent if 1h bars)
        # Real VWAP needs volume weighting.
        vwap = vwap_session(df['high'], df['low'], df['close'], df['volume'], df.index.to_series())
        
        # Logic
        # Newest closed bar is at [-1]
        curr_dir = st_dir.iloc[-1]
        curr_close = df['close'].iloc[-1]
        curr_vwap = vwap.iloc[-1]
        
        # Check for FLIP
        # We need state to know if it flipped THIS bar.
        # But wait, we can check previous bar in series.
        prev_dir_series = st_dir.iloc[-2]
        
        # Signal Generation
        signal_side = None
        
        # Long Entry: ST flips to 1 AND Close > VWAP
        if curr_dir == 1 and prev_dir_series == -1:
            if curr_close > curr_vwap:
                signal_side = "LONG"
                
        # Short Entry: ST flips to -1 AND Close < VWAP
        elif curr_dir == -1 and prev_dir_series == 1:
            if curr_close < curr_vwap:
                signal_side = "SHORT"
                
        if signal_side:
            return SignalEvent(
                ts=bars[-1].ts, # Timestamp of the closed bar
                symbol=symbol,
                portfolio_id="HONG", # From config
                strategy_id=self.strategy_id,
                direction=signal_side,
                timeframe=timeframe,
                regime="TREND",
                confidence=1.0
            )
            
        return None
