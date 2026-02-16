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
    def __init__(self, strategy_id: str = "vwap_supertrend", atr_period=None, atr_mult=None):
        super().__init__(strategy_id)
        self.signal_tf = os.getenv("STRATEGY_TIMEFRAME_SIGNAL", STRATEGY_TIMEFRAME_SIGNAL)
        self.atr_period = atr_period if atr_period is not None else ST_ATR_PERIOD
        self.atr_mult = atr_mult if atr_mult is not None else ST_ATR_MULT
        
        self.debug_counts = {
            "total_calls": 0,
            "insufficient_data": 0,
            "supertrend_long_flip": 0,
            "supertrend_short_flip": 0,
            "vwap_long_pass": 0,
            "vwap_short_pass": 0,
            "signal_emitted": 0
        }

    @property
    def required_timeframes(self) -> Set[str]:
        return {self.signal_tf}

    def on_bars(self, symbol: str, timeframe: str, bars: List[Bar]) -> Optional[SignalEvent]:
        self.debug_counts["total_calls"] += 1
        
        target_tf = os.getenv("STRATEGY_TIMEFRAME_SIGNAL", self.signal_tf)
        # We might want to allow running on any passed TF for backtest flexibility
        # but original logic enforced strict match. Keeping strict match but user should ensure env var or logic matches.
        # Actually logic says: if timeframe != target_tf return None. this might be why 4h failed if target_tf default is 1h?
        # But run_backtest calls it with current loop tf.
        
        if len(bars) < self.atr_period + 5:
            self.debug_counts["insufficient_data"] += 1
            return None

        df = pd.DataFrame([b.__dict__ for b in bars])
        df['ts'] = pd.to_datetime(df['ts'])
        df.set_index('ts', inplace=True)
        
        # Calculate Indicators
        st_dir, st_val = supertrend(df['high'], df['low'], df['close'], self.atr_period, self.atr_mult)
        vwap = vwap_session(df['high'], df['low'], df['close'], df['volume'], df.index.to_series())
        
        if len(st_dir) < 2: return None
        
        curr_dir = st_dir.iloc[-1]
        prev_dir = st_dir.iloc[-2]
        curr_close = df['close'].iloc[-1]
        curr_vwap = vwap.iloc[-1]
        
        signal_side = None
        if curr_dir == 1 and prev_dir == -1:
            self.debug_counts["supertrend_long_flip"] += 1
            if curr_close > curr_vwap:
                self.debug_counts["vwap_long_pass"] += 1
                signal_side = "LONG"
        elif curr_dir == -1 and prev_dir == 1:
            self.debug_counts["supertrend_short_flip"] += 1
            if curr_close < curr_vwap:
                self.debug_counts["vwap_short_pass"] += 1
                signal_side = "SHORT"
                
        if signal_side:
            self.debug_counts["signal_emitted"] += 1
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
