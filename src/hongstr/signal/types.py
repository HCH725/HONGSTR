from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import pandas as pd

@dataclass(frozen=True)
class Bar:
    ts: pd.Timestamp
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool = False
    
    @property
    def timestamp(self) -> pd.Timestamp:
        return self.ts

@dataclass
class SignalEvent:
    ts: pd.Timestamp
    symbol: str
    portfolio_id: str
    strategy_id: str
    direction: str  # 'LONG', 'SHORT', 'FLAT'
    timeframe: str
    regime: str = "NEUTRAL"
    confidence: float = 1.0
    reason: str = ""
    source: str = "realtime"
    
    def to_dict(self):
        return {
            "ts": self.ts.isoformat(),
            "symbol": self.symbol,
            "portfolio_id": self.portfolio_id,
            "strategy_id": self.strategy_id,
            "direction": self.direction,
            "timeframe": self.timeframe,
            "regime": self.regime,
            "confidence": self.confidence,
            "reason": self.reason,
            "source": self.source
        }

@dataclass
class EngineConfig:
    symbols: List[str]
    timeframes: List[str]
    input_root: str
    output_root: str
    state_root: str
    mode: str = "tail_jsonl" # tail_jsonl, batch_dir
    max_bars: int = 1000
