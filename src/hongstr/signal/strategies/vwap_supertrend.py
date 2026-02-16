from typing import List, Set, Optional
import pandas as pd
from ..types import Bar, SignalEvent
from .base import BaseStrategy
from ..indicators import supertrend, vwap_session
from ...config import (
    ST_ATR_PERIOD, ST_ATR_MULT, VWAP_ANCHOR, VWAP_BAND_STD,
    STRATEGY_TIMEFRAME_BASE, STRATEGY_TIMEFRAME_SIGNAL
)
import os

class VWAPSupertrendStrategy(BaseStrategy):
    def __init__(self, strategy_id: str = "vwap_supertrend"):
        super().__init__(strategy_id)
        self.signal_tf = os.getenv("STRATEGY_TIMEFRAME_SIGNAL", STRATEGY_TIMEFRAME_SIGNAL)

    @property
    def required_timeframes(self) -> Set[str]:
        return {self.signal_tf}

    def on_bars(self, symbol: str, timeframe: str, bars: List[Bar]) -> Optional[SignalEvent]:
        target_tf = os.getenv("STRATEGY_TIMEFRAME_SIGNAL", self.signal_tf)
        if timeframe != target_tf:
            return None
            
        if len(bars) < ST_ATR_PERIOD + 5:
            return None

        df = pd.DataFrame([b.__dict__ for b in bars])
        df['ts'] = pd.to_datetime(df['ts'])
        df.set_index('ts', inplace=True)
        
        # Calculate Indicators
        st_dir, st_val = supertrend(df['high'], df['low'], df['close'], ST_ATR_PERIOD, ST_ATR_MULT)
        vwap = vwap_session(df['high'], df['low'], df['close'], df['volume'], df.index.to_series())
        
        if len(st_dir) < 2: return None
        
        curr_dir = st_dir.iloc[-1]
        prev_dir = st_dir.iloc[-2]
        curr_close = df['close'].iloc[-1]
        curr_vwap = vwap.iloc[-1]
        
        signal_side = None
        if curr_dir == 1 and prev_dir == -1:
            if curr_close > curr_vwap:
                signal_side = "LONG"
        elif curr_dir == -1 and prev_dir == 1:
            if curr_close < curr_vwap:
                signal_side = "SHORT"
                
        if signal_side:
            return SignalEvent(
                ts=bars[-1].ts, 
                symbol=symbol,
                portfolio_id="HONG",
                strategy_id=self.strategy_id,
                direction=signal_side,
                timeframe=timeframe,
                regime="TREND",
                confidence=1.0
            )
        return None
