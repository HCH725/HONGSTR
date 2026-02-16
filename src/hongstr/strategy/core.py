from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd

@dataclass
class SignalEvent:
    ts: pd.Timestamp
    symbol: str
    portfolio_id: str
    strategy_id: str
    direction: str  # 'LONG', 'SHORT', 'FLAT'
    confidence: float = 1.0

class StrategyTemplate(ABC):
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id

    @property
    @abstractmethod
    def required_timeframes(self) -> List[str]:
        """List of required timeframes (e.g., ['1h', '4h'])"""
        pass

    @property
    def param_schema(self) -> Dict[str, Any]:
        """Metadata for parameters (defaults, ranges)"""
        return {}

    @abstractmethod
    def compute_features(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Compute necessary features/indicators"""
        pass

    @abstractmethod
    def signal(self, row: pd.Series, params: Dict[str, Any]) -> str:
        """Return 'LONG', 'SHORT', 'FLAT' for a given row"""
        pass
